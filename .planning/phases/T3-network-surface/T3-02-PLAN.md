---
phase: T3-network-surface
plan: 02
type: execute
wave: 1
depends_on: [T3-01]
files_modified:
  - voss/harness/tools.py
  - voss/harness/permissions.py
  - voss_runtime/_config.py
  - voss/harness/config.py
  - voss/harness/cli.py
  - tests/harness/test_allow_net.py
  - tests/harness/test_agent_config.py
autonomous: true
requirements: [NET-05]
must_haves:
  truths:
    - "ToolEntry has a stored field is_network: bool = False (additive; preserves frozen dataclass and all existing constructions)"
    - "make_toolset signature becomes make_toolset(cwd: Path, *, net: NetSession | None = None) and remains backward-compatible (every existing make_toolset(cwd) call site keeps working)"
    - "RuntimeConfig has a field allow_net: bool = False"
    - "voss/harness/config.py exposes get_allow_net() that reads [tools] allow_net from ~/.config/voss/config.toml with default False"
    - "voss/harness/permissions.py PermissionGate.check accepts a new is_network kwarg; when is_network=True and runtime.allow_net=False the gate returns (False, 'net disabled: set tools.allow_net = true in harness.toml or pass --allow-net') BEFORE mode-tier evaluation"
    - "cli.py do/chat commands accept --allow-net flag; flag presence calls configure(allow_net=True); flag absence preserves prior configure-from-TOML value"
    - "All six NET-05 acceptance bullets pass via tests/harness/test_allow_net.py"
  artifacts:
    - path: "voss/harness/tools.py"
      provides: "is_network: bool = False field on ToolEntry; make_toolset(cwd, *, net=None) signature"
      contains: "is_network"
    - path: "voss/harness/permissions.py"
      provides: "PermissionGate.check + _check_impl accept is_network kwarg; net-check inserted between project-policy deny and mode-tier"
      contains: "is_network"
    - path: "voss_runtime/_config.py"
      provides: "RuntimeConfig.allow_net: bool = False field"
      contains: "allow_net"
    - path: "voss/harness/config.py"
      provides: "_TOOLS_BLOCK regex + get_allow_net() loader following get_max_iterations pattern at line 70"
      contains: "def get_allow_net"
    - path: "voss/harness/cli.py"
      provides: "--allow-net flag on do_cmd and chat_cmd; configure(allow_net=True) on flag presence"
      contains: "allow_net"
    - path: "tests/harness/test_allow_net.py"
      provides: "6 NET-05 acceptance tests replace pytest.skip stubs from T3-01"
      contains: "def test_zero_socket_invariant"
  key_links:
    - from: "voss/harness/permissions.py:_check_impl"
      to: "voss_runtime._config.get_config().allow_net"
      via: "if is_network and not get_config().allow_net: return (False, 'net disabled: ...')"
      pattern: "get_config\\(\\)\\.allow_net"
    - from: "voss/harness/cli.py do_cmd / chat_cmd"
      to: "voss_runtime.configure"
      via: "if allow_net: configure(allow_net=True)"
      pattern: "configure\\(allow_net=True\\)"
    - from: "voss/harness/tools.py:make_toolset"
      to: "voss/harness/net.py NetSession (created in T3-05)"
      via: "optional net: NetSession | None kwarg; when None, network tool bodies short-circuit to disabled-error envelope"
      pattern: "net:\\s*\"?NetSession"
---

<objective>
Lay the permission + config foundation that all subsequent web/MCP plans build on: the `is_network` boolean axis on `ToolEntry` (D-09), the `make_toolset(cwd, *, net=None)` backward-compatible kwarg (D-08), `RuntimeConfig.allow_net` field with TOML loader (NET-05a..d), `PermissionGate.check` net-gate firing before mode-tier (NET-05e + D-10), and the `--allow-net` CLI flag plumbed through `do` and `chat` commands.

Purpose: NET-05 is the safety invariant. The zero-socket assertion (NET-05f) is load-bearing — without this gate, all later network code would default to "on", reversing the SPEC's network-off-by-default posture. T3-05/06/07 all consume `ToolEntry.is_network` from this plan; without the field, network tools cannot be registered correctly.

Output: 6 test functions un-skipped in tests/harness/test_allow_net.py (all pass); `is_network` field on ToolEntry; `make_toolset` accepts `net` kwarg; `RuntimeConfig.allow_net` field + `get_allow_net()` loader; `--allow-net` flag on `voss do` and `voss chat`. No new files created; all changes are additive extensions.
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
@.planning/phases/T2-parallel-tools-multi-edit/T2-02-PLAN.md
@.planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-PLAN.md
@voss/harness/tools.py
@voss/harness/permissions.py
@voss/harness/config.py
@voss_runtime/_config.py
@voss/harness/cli.py
</context>

<interfaces>
Current ToolEntry shape (voss/harness/tools.py lines 14-23, FROZEN dataclass):
```
@dataclass(frozen=True)
class ToolEntry:
    descriptor: ToolDescriptor
    is_mutating: bool
    # T3-02 adds: is_network: bool = False
```
Adding a field with a default to a frozen dataclass is safe; existing positional/keyword constructions in tools.py lines 197-207 remain valid.

Current make_toolset signature (voss/harness/tools.py line 44):
```
def make_toolset(cwd: Path) -> dict[str, ToolEntry]:
```
Extension: `def make_toolset(cwd: Path, *, net: "NetSession | None" = None) -> dict[str, ToolEntry]:`
String forward-ref for NetSession avoids importing voss/harness/net.py (which T3-05 creates). At T3-02 execution time, the import is wrapped in `if TYPE_CHECKING:` at the top of tools.py.

Current PermissionGate.check (voss/harness/permissions.py line 169):
```
def check(self, tool_name: str, args: dict, *, is_mutating: bool = False) -> tuple[bool, str]:
    allowed, why = self._check_impl(tool_name, args, is_mutating=is_mutating)
```
Extension: add `is_network: bool = False` kwarg; pass through to _check_impl. The telemetry emission block in check() (the existing emit_permission_result call site) STILL fires on net-denial (consistent with D-10 "no net.request event on denial" — telemetry.permission.result is unaffected; only net.request is suppressed, and net.request originates from T3-05's NetSession, not from this gate).

Current _check_impl (voss/harness/permissions.py line 187): project-policy deny → mode-tier → deny-rules → prompt. Insert the net-check between project-policy and mode-tier (exact insertion point — T3-PATTERNS.md "voss/harness/permissions.py (extend)" section locks this ordering).

Current RuntimeConfig (voss_runtime/_config.py line 19): has `max_iterations: int = 8` (T1-04) and `max_parallel_reads: int = 8` (T2-02). Add `allow_net: bool = False` after these. `configure(**kwargs)` already generic via dataclasses.replace — no change needed.

Current voss/harness/config.py: lines 25-26 define `_HARNESS_BLOCK` + `_AGENT_BLOCK` regex. Lines 30-44 define `_parse_*_section` helpers; lines 46-67 define `load_*_config` accessors; line 70 defines `get_max_iterations` (the EXACT pattern this plan mirrors).

Current cli.py: do_cmd at line 904, chat_cmd at line 1039, edit_cmd at line 1093. Each has a `@click.option("--yes", "yes_to_all", is_flag=True, ...)` line (line 922 for do_cmd). Add `@click.option("--allow-net/--no-allow-net", "allow_net", default=None, help="Enable (--allow-net) or disable (--no-allow-net) network tools for this session (web_fetch, web_search, MCP). When neither is passed, the [tools] allow_net setting from config.toml is used.")` immediately after the --yes option in BOTH do_cmd and chat_cmd. Use the `--flag/--no-flag` pair with `default=None` so we get tri-state semantics: None (no flag passed → fall back to TOML), True (`--allow-net`), False (`--no-allow-net`). SPEC NET-05d criterion `voss --allow-net=false` is satisfied via the click-idiomatic `voss --no-allow-net` form; click `--flag/--no-flag` pairs do not accept `--flag=value` syntax. Then inside the command body add a configure() call:

```
if allow_net is True:
    configure(allow_net=True)
elif allow_net is False:
    configure(allow_net=False)
# else allow_net is None: TOML setting applied at boot wins
```

Bootstrap-from-TOML wire-in: at cli.py module import (top-level, after T1-04/T2-02 configure() block — `grep -n "configure(\|max_iterations" voss/harness/cli.py` to locate exactly), extend the existing `configure(max_iterations=..., max_parallel_reads=...)` call to also pass `allow_net=get_allow_net()`. If no such bootstrap exists (T1-04/T2-02 haven't shipped wave order is preserved per STATE.md so they did), add the line; document in SUMMARY if it had to be added.

Test fixture pattern (from tests/harness/test_agent_config.py — already exists per T1-04):
```
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

Zero-socket invariant test (NET-05f): use httpx.MockTransport per RESEARCH Code Examples + T3-RESEARCH Common Pitfalls Pitfall 5. Construct a counting transport, instantiate an httpx.AsyncClient(transport=transport), inject it through a future NetSession constructor — but since NetSession doesn't exist yet (T3-05), this test stays partly future-bound. SHIPPABLE PROOF AT T3-02: call PermissionGate.check directly with is_network=True, allow_net=False, assert the denial returns BEFORE any tool body would run. The MockTransport+NetSession integration variant lands in T3-05's test refinement (T3-05 expands test_zero_socket_invariant; T3-02 ships the gate-only assertion).

To make test_zero_socket_invariant pass at T3-02 time WITHOUT NetSession existing, write it as a gate-only check: build a fake ToolEntry-shaped object with is_network=True, call gate.check("fake_net_tool", {}, is_network=True), assert (False, "net disabled: ...") returned. Mark a comment in the test body "Zero-socket invariant — final NetSession+MockTransport variant lands in T3-05". This is acceptable because the actual ToolEntry.is_network → gate ordering is the load-bearing safety; the httpx-level integration is belt-and-suspenders.
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add is_network to ToolEntry + net kwarg to make_toolset + allow_net to RuntimeConfig + get_allow_net loader</name>
  <files>voss/harness/tools.py, voss_runtime/_config.py, voss/harness/config.py, tests/harness/test_agent_config.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-05a, NET-05b — default False, TOML override)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-08, D-09)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (sections "voss/harness/tools.py (extend)" + "voss_runtime/_config.py (extend)" + "voss/harness/config.py (extend)")
    - voss/harness/tools.py lines 14-44 (ToolEntry + make_toolset signature)
    - voss/harness/config.py lines 25-86 (_HARNESS_BLOCK pattern + get_max_iterations exact template)
    - voss_runtime/_config.py (RuntimeConfig field declaration site after max_parallel_reads)
    - tests/harness/test_agent_config.py (xdg fixture pattern to extend)
    - .planning/phases/T1-iteration-loop-streaming-interrupt/T1-04-PLAN.md (set_max_iterations writer pattern — NOT needed for allow_net since SPEC only requires reader)
  </read_first>
  <action>
    Edit voss/harness/tools.py:
    - At top of file, under existing imports, add `from typing import TYPE_CHECKING` if absent. Add a `TYPE_CHECKING` block: `if TYPE_CHECKING:\n    from voss.harness.net import NetSession`. This avoids a circular import at runtime; only IDE/type-checkers resolve the forward ref.
    - In the @dataclass(frozen=True) class ToolEntry block (line 14-23): add `is_network: bool = False` as the third field after `is_mutating: bool`. Update the docstring to mention "is_network drives the allow_net gate in PermissionGate (T3-02). Independent of is_mutating."
    - Update make_toolset signature on line 44: `def make_toolset(cwd: Path, *, net: "NetSession | None" = None) -> dict[str, ToolEntry]:`. The kwarg-only `*,` separator means existing positional `make_toolset(cwd)` calls work unchanged.
    - Do NOT register any new ToolEntry yet (web_fetch / web_search land in T3-05/T3-06). Do NOT change any existing ToolEntry construction at lines 197-207.

    Edit voss_runtime/_config.py:
    - In RuntimeConfig dataclass, after the `max_parallel_reads: int = 8` field (T2-02), add:
      `allow_net: bool = False` with an inline comment matching T1-04/T2-02 style: "# T3-02: network access opt-in. CLI flag --allow-net or [tools] allow_net = true in ~/.config/voss/config.toml. PermissionGate reads via get_config().allow_net."
    - No change to configure() — it's already dataclasses.replace based.

    Edit voss/harness/config.py:
    - After `_AGENT_BLOCK` on line 26, add: `_TOOLS_BLOCK = re.compile(r"^\[tools\][^\[]*", re.MULTILINE)`.
    - After get_max_iterations() (around line 86), add `_parse_tools_section` and `load_tools_config` mirroring `_parse_agent_section`/`load_agent_config` lines 38-67.
    - Add `def get_allow_net() -> bool:` mirroring get_max_iterations EXACTLY (lines 70-86):
      - default = RuntimeConfig().allow_net  (resolves to False — sources the default from the dataclass, not a hardcoded literal)
      - cfg = load_tools_config()
      - raw = cfg.get("allow_net")
      - if raw is None: return default
      - normalize raw lowercased: if raw == "true": return True; if raw == "false": return False
      - on any other value: warnings.warn(f'[tools] allow_net = {raw!r} is not a boolean; falling back to default False', RuntimeWarning, stacklevel=2); return default
    - Do NOT add set_allow_net (no SPEC writer requirement).
    - PITFALL gate: the existing `_KV` regex matches double-quoted strings only. The TOML `allow_net = true` is bare (no quotes). Either add a parallel `_KV_BOOL = re.compile(r'^\s*allow_net\s*=\s*(true|false)\s*$', re.MULTILINE)` and call it inside _parse_tools_section, OR document explicitly in _parse_tools_section that boolean values use a different regex from `_KV`. Pick the parallel regex approach (matches T3-PATTERNS Pitfall 6 and T3-RESEARCH Pattern 7). Run the regex against a fixture string with `[tools]\nallow_net = true\n` before declaring success.

    Edit tests/harness/test_agent_config.py:
    - Add 4 new tests for get_allow_net (NET-05a/b only — NET-05c/d are CLI tests in Task 2; NET-05e/f are gate tests in Task 2):
      - `test_get_allow_net_default_false(xdg)`: no config.toml exists. Assert `get_allow_net() is False`.
      - `test_get_allow_net_toml_true(xdg)`: write `[tools]\nallow_net = true\n` to xdg/voss/config.toml. Assert `get_allow_net() is True`.
      - `test_get_allow_net_toml_false_explicit(xdg)`: write `[tools]\nallow_net = false\n`. Assert `get_allow_net() is False`.
      - `test_get_allow_net_bogus_warns(xdg)`: write `[tools]\nallow_net = yes\n`. Use `pytest.warns(RuntimeWarning, match="allow_net")`; assert `get_allow_net() is False` (fallback to default).
    - Also add `test_three_keys_coexist`: write a config.toml with `[harness]\npreferred_model = "foo"\n\n[agent]\nmax_iterations = "12"\nmax_parallel_reads = "16"\n\n[tools]\nallow_net = true\n`. Assert load_harness_config/load_agent_config/load_tools_config each return the expected key without erasing the others (cross-section round-trip invariant; mirrors T2-02's both-keys-roundtrip test).
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_agent_config.py -x -q -k "allow_net or three_keys" 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -n "is_network:\s*bool\s*=\s*False" voss/harness/tools.py` returns 1 match
    - source assertion: `grep -nE "def make_toolset\(cwd: Path,\s*\*,\s*net:" voss/harness/tools.py` returns 1 match (kwarg-only net parameter)
    - source assertion: `grep -nE "allow_net:\s*bool\s*=\s*False" voss_runtime/_config.py` returns 1 match
    - source assertion: `grep -n "def get_allow_net\|_TOOLS_BLOCK\|load_tools_config" voss/harness/config.py | wc -l` >= 3
    - regex correctness: `python -c "import re; r=re.compile(r'^\[tools\][^\[]*', re.MULTILINE); print(bool(r.search('[tools]\nallow_net = true\n')))"` prints `True`
    - default assertion: `python -c "from voss_runtime import RuntimeConfig; print(RuntimeConfig().allow_net)"` prints `False`
    - behavior: all 5 new tests pass (test_get_allow_net_default_false, test_get_allow_net_toml_true, test_get_allow_net_toml_false_explicit, test_get_allow_net_bogus_warns, test_three_keys_coexist)
    - regression: `uv run pytest tests/harness/test_agent_config.py tests/harness/test_harness_config.py -x -q` exits 0 (T1-04 + T2-02 tests still pass)
    - import isolation: `grep -nE "from voss.harness.net import|import.*voss.harness.net" voss/harness/tools.py | grep -v TYPE_CHECKING` returns 0 matches (NetSession import is TYPE_CHECKING-only)
  </acceptance_criteria>
  <done>ToolEntry has is_network field; make_toolset accepts net kwarg via forward-ref; RuntimeConfig.allow_net default False; get_allow_net reads [tools] allow_net with bogus-value warning + fallback; three sections coexist in one config.toml; no NetSession import added at runtime.</done>
</task>

<task type="auto">
  <name>Task 2: PermissionGate net-check + --allow-net CLI flag + NET-05 acceptance tests</name>
  <files>voss/harness/permissions.py, voss/harness/cli.py, tests/harness/test_allow_net.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-05 acceptance bullets a-f)
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-10 — net-check before mode-tier; D-12 — denial UX string)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (sections "voss/harness/permissions.py (extend)" + "voss/harness/cli.py (extend)" + "PermissionGate Structural Denial Test Pattern")
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (Pattern 8 — PermissionGate.check insertion point)
    - voss/harness/permissions.py lines 169-204 (check + _check_impl flow)
    - voss/harness/cli.py lines 904-940 (do_cmd full decorator stack and signature)
    - voss/harness/cli.py lines 1039-1090 (chat_cmd full decorator stack)
    - tests/harness/test_permissions_modes.py lines 43-53 (_fail_prompt structural-denial test pattern)
    - tests/harness/test_allow_net.py (T3-01 scaffold — 6 pytest.skip stubs to replace)
  </read_first>
  <action>
    Edit voss/harness/permissions.py:
    - Update check() signature (line 169): `def check(self, tool_name: str, args: dict, *, is_mutating: bool = False, is_network: bool = False) -> tuple[bool, str]:`
    - Pass through to _check_impl: `allowed, why = self._check_impl(tool_name, args, is_mutating=is_mutating, is_network=is_network)`
    - Update _check_impl signature (line 187): `def _check_impl(self, tool_name: str, args: dict, *, is_mutating: bool = False, is_network: bool = False) -> tuple[bool, str]:`
    - Insert net-check between project-policy deny (existing line ~189) and mode-tier (existing line ~204). Code shape:
      - `if is_network:`
      - `    from voss_runtime._config import get_config`  (local import to avoid module-level cycle)
      - `    if not get_config().allow_net:`
      - `        return False, "net disabled: set tools.allow_net = true in harness.toml or pass --allow-net"`
    - Do NOT add any telemetry emit in this branch — the net.request event lives in NetSession (T3-05), and the existing permission.result emit in check() still fires post-denial-return (it always fires for any denial; that's by design and consistent with current behavior).
    - PRESERVE every other line of check / _check_impl — surgical insertion only.

    Audit callers of gate.check to confirm none break: `grep -rn "\.check(" voss/harness/` for `gate.check(`/`permission_gate.check(` patterns. Existing callers pass `is_mutating=...` as kwarg or omit; adding a new kwarg with default=False is backward-compatible. Note in SUMMARY any caller that should pass `is_network=entry.is_network` going forward (T3-05's web_fetch tool wiring will do that — out of scope for T3-02).

    Edit voss/harness/cli.py:
    - Locate do_cmd (line 904) and chat_cmd (line 1039). For each command:
      - Add `@click.option("--allow-net/--no-allow-net", "allow_net", default=None, help="Enable (--allow-net) or disable (--no-allow-net) network tools (web_fetch, web_search, MCP) for this session. When neither is passed, falls back to [tools] allow_net in config.toml. NOTE: SPEC NET-05d criterion `voss --allow-net=false` is satisfied via the click-idiomatic `voss --no-allow-net` form — click is_flag pairs do not accept `--flag=value` syntax.")` immediately after the `@click.option("--yes", ...)` line.
      - Add `allow_net: bool | None` to the function signature (tri-state: None = no flag passed, True = `--allow-net`, False = `--no-allow-net`).
      - In the function body, after `_resolve_default_model(model)` (line 940-ish in do_cmd), add:
        ```
        if allow_net is True:
            configure(allow_net=True)
        elif allow_net is False:
            configure(allow_net=False)
        # else allow_net is None: TOML default applied at bootstrap wins
        ```
      - The tri-state with `default=None` is what lets the CLI override config-file `true` to False via `voss --no-allow-net` (SPEC NET-05d). When the flag is omitted entirely, the bootstrap configure() call already established the TOML value — no extra branch needed. SPEC NET-05d acceptance criterion `voss --allow-net=false` is interpreted as the click-idiomatic `voss --no-allow-net` and must be explicitly documented in Task 2 acceptance below + in test docstrings.
    - Locate the existing cli.py bootstrap configure() call (T1-04 / T2-02 wrote: `configure(max_iterations=get_max_iterations(), max_parallel_reads=get_max_parallel_reads())` — `grep -n "configure(\|get_max_iterations\|get_max_parallel_reads" voss/harness/cli.py` to find the exact line). Extend that call to include `allow_net=get_allow_net()`. Also extend the import line `from voss.harness.config import get_max_iterations, get_max_parallel_reads` to `from voss.harness.config import get_max_iterations, get_max_parallel_reads, get_allow_net`. If the T1-04/T2-02 bootstrap configure() call does not exist (executor must check — `grep -nc "configure(max_iterations" voss/harness/cli.py`), the executor adds it as part of this task and notes in SUMMARY.

    Edit tests/harness/test_allow_net.py (replaces T3-01 placeholder skips):
    - Remove `pytest.skip(...)` lines. Add the standard test fixtures at the top (xdg, _reset_runtime — copy from tests/harness/test_agent_config.py).
    - `test_default_false(xdg)`: `reset_config(); assert get_config().allow_net is False`.
    - `test_toml_true(xdg)`: write `[tools]\nallow_net = true\n` to xdg/voss/config.toml; call `configure(allow_net=get_allow_net())`; assert `get_config().allow_net is True`.
    - `test_cli_override(xdg)`: write `[tools]\nallow_net = false\n`. Use click.testing.CliRunner to invoke `do --allow-net "noop"`. Because do_cmd does real work, mock the auth + provider entry points OR use a smaller verification — alternative: directly call the configure() block by importing do_cmd's body logic. SIMPLER PATH: write `test_cli_override` as a subprocess test (mirror T2-02 Task 2 pattern):
      ```
      subprocess.run([sys.executable, "-c",
        "import sys; sys.argv=['voss','do','--allow-net','--help']; "
        "from voss.harness.cli import do_cmd; "
        "# but --help short-circuits — instead inspect: "
        "from click.testing import CliRunner; "
        "from voss.harness.cli import do_cmd; "
        "r = CliRunner().invoke(do_cmd, ['--allow-net','--help']); "
        "print('OK' if '--allow-net' in r.output else 'MISSING')"],
        env={**os.environ, "XDG_CONFIG_HOME": str(xdg)}, capture_output=True, text=True)
      ```
      Assert "OK" in stdout. This proves the flag is wired without running do_cmd's full body. For the actual override semantics, ALSO write a unit-level test:
      ```
      reset_config()
      # simulate TOML-side load of False:
      configure(allow_net=False)
      assert get_config().allow_net is False
      # simulate CLI flag flipping it:
      configure(allow_net=True)
      assert get_config().allow_net is True
      ```
      Document in test body that the actual --allow-net flag is verified via the CliRunner --help inspection above.
    - `test_cli_explicit_false(xdg)`: SPEC NET-05d "`voss --allow-net=false` overrides config-file `true` to False" is satisfied via the click-idiomatic flag pair `voss --no-allow-net`. The click option is declared as `--allow-net/--no-allow-net` with `default=None` (tri-state). Verify all three CLI cases:
      1. **`--allow-net` present + TOML=false** → final allow_net is True. Simulate by `configure(allow_net=False)` (TOML load) then the do_cmd body branch `if allow_net is True: configure(allow_net=True)`; assert `get_config().allow_net is True`.
      2. **`--no-allow-net` present + TOML=true** → final allow_net is False. Simulate by `configure(allow_net=True)` (TOML load) then `configure(allow_net=False)` (CLI --no-allow-net branch); assert `get_config().allow_net is False`. This is the literal SPEC NET-05d coverage.
      3. **Neither flag + TOML=true** → final allow_net is True (TOML wins when CLI is absent / allow_net is None). Simulate by `configure(allow_net=True)` and no further configure() call; assert `get_config().allow_net is True`.
      Also use CliRunner to verify both flag spellings are recognized by do_cmd: `CliRunner().invoke(do_cmd, ["--allow-net", "--help"])` and `CliRunner().invoke(do_cmd, ["--no-allow-net", "--help"])` both exit 0; assert `--allow-net` and `--no-allow-net` both appear in `do_cmd --help` output. Document in the test docstring: "SPEC NET-05d `--allow-net=false` is implemented as the click-idiomatic `--no-allow-net`; click `--flag/--no-flag` pairs do not accept `=value` syntax. The override semantics (CLI > TOML > default) are identical regardless of surface syntax."
    - `test_gate_before_prompt(xdg)`: copy structural-denial pattern from tests/harness/test_permissions_modes.py lines 43-53. Create a `PermissionGate(mode="edit", store=PermissionStore(cwd=tmp_path))`. Set `gate.prompt_fn = _fail_prompt` (raises pytest.fail on call). Call `allowed, why = gate.check("web_fetch", {"url": "https://x.com"}, is_mutating=False, is_network=True)` with `configure(allow_net=False)` first. Assert `allowed is False` and `"net disabled" in why`. Repeat with `configure(allow_net=True)` and assert `allowed is True or prompt_fn was called` (mode-tier may continue to prompt — that's OK; the assertion is "net-gate did not deny when allow_net=True").
    - `test_zero_socket_invariant(xdg)`: gate-level proof. Construct a fake ToolEntry-shaped object with is_network=True. Call gate.check with is_network=True, allow_net=False, assert denial returned BEFORE any network code path runs. Use a counter pattern: monkeypatch a sentinel function that would be called if the tool body ran; assert sentinel counter remains 0. Comment in test body: `# Belt-and-suspenders httpx MockTransport variant lands in T3-05; T3-02 ships the gate-level proof which is the load-bearing safety invariant per D-10.`

    Run the 6 tests; ensure all pass. Confirm pytest.skip strings are fully removed from this file via `grep -c "pytest.skip" tests/harness/test_allow_net.py` returning 0.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_allow_net.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "is_network:\s*bool\s*=\s*False" voss/harness/permissions.py | wc -l` returns 2 (check + _check_impl signatures)
    - source assertion: `grep -nE "net disabled: set tools.allow_net" voss/harness/permissions.py` returns 1 match (exact NET-05 envelope string)
    - source assertion: `grep -cE "--allow-net/--no-allow-net" voss/harness/cli.py` returns >= 2 (do_cmd + chat_cmd click.option declare the flag pair)
    - source assertion: `grep -nE "configure\(allow_net=False\)" voss/harness/cli.py | wc -l` >= 2 (--no-allow-net branch in do_cmd + chat_cmd bodies)
    - source assertion: `grep -nE "configure\(allow_net=True\)" voss/harness/cli.py | wc -l` returns >= 2 (do_cmd + chat_cmd bodies)
    - bootstrap assertion: `grep -nE "configure\([^)]*allow_net=get_allow_net" voss/harness/cli.py` returns >= 1 (TOML→runtime wire)
    - skip removed: `grep -c "pytest.skip" tests/harness/test_allow_net.py` returns 0
    - behavior: all 6 NET-05 tests pass (test_default_false, test_toml_true, test_cli_override, test_cli_explicit_false, test_gate_before_prompt, test_zero_socket_invariant)
    - regression: `uv run pytest tests/harness/test_permissions_modes.py tests/harness/test_agent_config.py tests/harness/test_allow_net.py -x -q` exits 0
    - lint: existing PermissionGate test callers (`grep -rn "\.check(" tests/` for any caller passing positional args that would break with new kwargs) still pass
  </acceptance_criteria>
  <done>PermissionGate.check + _check_impl accept is_network kwarg with net-gate inserted between project-policy deny and mode-tier; --allow-net flag wired into do_cmd and chat_cmd; cli.py boot configure() call includes allow_net=get_allow_net(); 6 NET-05 acceptance tests un-skipped and green; existing permissions tests unaffected.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Agent loop tool dispatch → network I/O | PermissionGate.check is the single chokepoint that decides whether any is_network=True tool body executes. A bypass here = SSRF / data exfiltration surface. |
| Local user → harness config | User-editable `~/.config/voss/config.toml` `[tools] allow_net` is trusted (local user authored their own file); but malformed values must not crash bootstrap. |
| CLI invocation → runtime config singleton | `--allow-net` flag must propagate via configure() to the same RuntimeConfig the gate reads; mismatch = enforcement asymmetry. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-01 | Elevation | Network tools enabled by default → unintended outbound calls | mitigate | `allow_net: bool = False` is the dataclass default; `get_allow_net()` returns False when no `[tools]` block; gate denies before any tool body sees the call; NET-05f zero-socket invariant proves this at the gate level. T3-05 expands the proof to the httpx-transport level. |
| T-T3-02-01 | Tampering | `[tools] allow_net = yes` (typo) silently enables net | mitigate | get_allow_net only accepts exact `true`/`false`; any other string emits RuntimeWarning + falls back to False (test_get_allow_net_bogus_warns proves) |
| T-T3-02-02 | DoS | malformed `[tools]` block crashes cli.py bootstrap | mitigate | get_allow_net wraps all parsing in path-exists / OSError guards mirroring get_max_iterations; on any failure returns the safe default (False) |
| T-T3-02-03 | Elevation | Caller forgets to pass `is_network=entry.is_network` to gate.check | accept | Default `is_network=False` means a forgotten kwarg falls through to mode-tier (existing behavior). T3-05 wires the dispatch site; an audit task in T3-05 verifies all `.check(` call sites pass is_network for network entries. SPEC NET-05f via gate-only proof remains valid because the gate gets called with the kwarg explicitly in the failing test. |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_allow_net.py tests/harness/test_agent_config.py tests/harness/test_permissions_modes.py -x -q` exits 0
- `grep -nE "is_network:\s*bool" voss/harness/tools.py voss/harness/permissions.py | wc -l` >= 3 (ToolEntry field + check sig + _check_impl sig)
- `grep -nE "allow_net" voss_runtime/_config.py voss/harness/config.py voss/harness/cli.py | wc -l` >= 4 (field + loader + boot wire + at least one CLI handler)
- `python -c "from voss_runtime import RuntimeConfig, get_config, reset_config; reset_config(); print(get_config().allow_net)"` prints `False`
- `python -c "from voss.harness.tools import ToolEntry; import dataclasses; print([f.name for f in dataclasses.fields(ToolEntry)])"` includes `'is_network'`
- NET-05 acceptance: a `PermissionGate.check("web_fetch", {}, is_network=True)` with `configure(allow_net=False)` returns `(False, 'net disabled: ...')` without invoking prompt_fn
</verification>

<success_criteria>
- 6 NET-05 acceptance tests pass; test_zero_socket_invariant proves no tool body runs when net-gate denies
- is_network field on ToolEntry; make_toolset gains net kwarg (signature compatible with existing call sites)
- RuntimeConfig.allow_net default False; TOML override via `[tools] allow_net = true`; `--allow-net` CLI flag forces True
- PermissionGate.check fires net-check between project-policy and mode-tier (D-10 order)
- Bootstrap wires get_allow_net() into the single configure() call alongside max_iterations + max_parallel_reads
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-02-SUMMARY.md` when done: record (a) exact line numbers of ToolEntry field addition, make_toolset signature change, RuntimeConfig field addition, _TOOLS_BLOCK regex addition, get_allow_net function; (b) cli.py bootstrap configure() call line number and exact contents post-extension; (c) pytest output showing 6 NET-05 tests green; (d) audit of `.check(` call sites in voss/harness/ noting which T3-05 must update to pass is_network.
</output>
