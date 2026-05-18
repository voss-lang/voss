# Phase M10 Pattern Mapping: Codebase Intelligence

**Role:** GSD `gsd-pattern-mapper`  
**Phase:** M10-agent-capability-surface-caps-01  
**Scope:** Patterns only. No source edits.  
**Inputs read:** `M10-CONTEXT.md`, `M10-RESEARCH.md`, `M10-SPEC.md`, Voss harness/TUI/test analogs.

## File Classification

| File | Change | Role | Data flow | Closest analog |
|---|---:|---|---|---|
| `.planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md` | new | prerequisite plan | planner creates M9 amendment before M10 execution | M9-02/M9-04 plan style, especially M9-04 side-region plan |
| `.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md` | modify | doc correction | `index.json` acceptance -> SQLite `.voss-cache/code/index.db` | no runtime analog; this is a one-line spec patch from CONTEXT |
| `voss/harness/code/__init__.py` | new | package surface | exports Voss-owned code-intel API, not pygls classes | package pattern: `voss/harness/mcp/__init__.py` |
| `voss/harness/code/models.py` | new | data models | service returns structured hits/envelopes to tools/slash/TUI/context | dataclass shape in `session.py`; strict schema style in `cognition_schemas.py` when config-bound |
| `voss/harness/code/config.py` | new | config loader | `.voss/lsp.yml` + packaged defaults -> language server registry config | `.voss/mcp.yml` loader in `voss/harness/mcp/config.py` |
| `voss/harness/code/defaults/lsp.yml` | new | packaged defaults | Python/JS/TS/Rust/Go server defaults overlaid by `.voss/lsp.yml` | pyproject package-data pattern for `harness/agent/*.voss` |
| `voss/harness/code/index.py` | new | rebuildable cache/index | cwd scan -> normalized files/symbol rows -> `.voss-cache/code/index.db` -> summary/query | `cognition.build_repo_idx()` plus `sandbox.write_cache()`; no SQLite analog |
| `voss/harness/code/ast_grep.py` | new | structural search backend | pattern/path -> `ast-grep run --json=stream` -> bounded hits; missing binary -> fallback request | `_shell_capture()` subprocess timeout/cap pattern; `fs_grep()` hit bounding |
| `voss/harness/code/regex_fallback.py` | new | soft-dependency fallback | indexed files + regex/pattern approximation -> bounded hits | `tools.fs_grep()` |
| `voss/harness/code/lsp.py` | new | LSP adapter | Voss result types <-> pygls client operations; no pygls types leak out | lifecycle subprocess pattern; MCP JSON-RPC client is only rough protocol analog |
| `voss/harness/code/lsp_registry.py` | new | lazy process registry | language -> one server process per session/cwd; register/reap on exit | `voss/harness/lifecycle.py` subprocess/job registries |
| `voss/harness/code/service.py` | new | orchestration facade | tools/slash/TUI call one `CodeIntelService`; service chooses index/LSP/ast-grep/regex | `MemoryStore(...).bind(session_id=...)` lazy service pattern; `make_toolset()` lazy closure pattern |
| `voss/harness/code/context.py` | new | system-context renderer | index summary -> bounded `## Project Index`, no raw snippets | `_compose_cognition_prompt()` and `_compose_system_blocks()` in `agent.py` |
| `voss/harness/tools.py` | modify | agent tool registry | four tool descriptors call `CodeIntelService`; entries are read-only | `ToolEntry`, `make_toolset()`, lazy local imports |
| `voss/harness/cli.py` | modify | session-start + slash wiring | session boot builds/refreshes index summary; slash commands route to service; TUI gets service/state | `_run_repl()` cognition load and slash dispatch patterns |
| `voss/harness/agent.py` | modify | system prompt injection | add `project_index_text` block into static prefix without destabilizing existing block order | `_compose_system_blocks()` cacheable block list |
| `voss/harness/render.py` | likely no protocol change | plain/json renderer boundary | `## Project Index` is prompt content, not renderer protocol; keep `--plain` byte contract stable | `PlainRenderer` no-op/status patterns |
| `voss/harness/tui/widgets/code_intel_panel.py` | new via M9-08 | TUI side widget | idle tree/results/focused excerpt state; no backend calls inside widget | `SubAgentPanel`, `TurnView`, `SlashPalette` Textual widgets |
| `voss/harness/tui/widgets/__init__.py` | modify via M9-08 | widget exports | expose `CodeIntelPanel` with existing public widget surface | existing widget re-export list |
| `voss/harness/tui/app.py` | modify via M9-08 | side-region state owner | CodeIntelPanel default; SubAgentPanel temporarily owns region during spawn; pin disables auto-switch | current `mount_subagent_panel()`/`collapse_subagent()` |
| `voss/harness/tui/renderer.py` | modify via M9-08/M10 | TUI bridge | private code-intel methods update app/panel; keep `Renderer` protocol unchanged unless unavoidable | private `show_subagent_*` extension methods |
| `voss/harness/tui/styles.tcss` | modify via M9-08 only if needed | side panel display rules | current `#side display:none` changes to visible-by-default CodeIntelPanel contract | current side-region CSS |
| `pyproject.toml` | modify | dependency/package data | add `code` optional extra and package defaults | existing `search` optional extra and package-data list |
| `tests/fixtures/code/{python,js,rust,go}/...` | new | fixture repos | minimal multi-language symbols/references/search cases | existing e2e fixture directory pattern |
| `tests/harness/code/test_index.py` | new | unit tests | temp repos -> deterministic SQLite schema/build/refresh/path jail | `tests/harness/test_cognition.py`, sandbox tests |
| `tests/harness/code/test_ast_grep.py` | new | unit tests | parser/fallback/timeout/malformed JSON/max-results | shell timeout + fs_grep style tests |
| `tests/harness/code/test_lsp_registry.py` | new | unit tests | fake server/lazy launch/missing command/reap | `tests/harness/test_lifecycle.py`, MCP client/config tests |
| `tests/harness/test_tools.py` | modify | registry assertions | expected read-only count + explicit code tools are non-mutating | current `TestToolEntryClassification` |
| `tests/harness/test_permissions_modes.py` / `tests/e2e/test_perm_matrix.py` | modify | read-only permission evidence | code tools allowed in plan/edit/auto via `is_mutating=False` | existing read-only mode rows |
| `tests/e2e/test_slash_matrix.py` | modify | slash coverage | add `/symbol`, `/refs`, `/refresh` rows and matrix coverage | existing matrix contract |
| `tests/harness/test_voss_md_injection.py` or new `test_project_index_injection.py` | modify/new | prompt injection tests | capture provider system blocks; assert `## Project Index`, no snippets, budget cap | existing VOSS.md injection capture helper |
| `tests/harness/tui/test_code_intel_panel.py` | new via M9-08 | widget/state tests | idle/results/focused/pin/SubAgentPanel precedence | `test_live_visualization.py`, `test_app_shell.py` |
| `tests/harness/tui/test_no_new_runtime_hooks.py` | unchanged gate | regression guard | M10 must pass without updating recorder/runtime baseline | existing baseline hash test |

## Pattern Assignments

### 1. Tool Registry And Read-Only Tool Shape

**Analog:** `voss/harness/tools.py:23-37`

Copy the explicit classification model:

```python
@dataclass(frozen=True)
class ToolEntry:
    descriptor: ToolDescriptor
    is_mutating: bool
    is_network: bool = False
```

`ToolEntry.is_mutating` is the permission source of truth. M10's four tools must register with `is_mutating=False`, not by adding names to `permissions.READ_ONLY`.

**Analog:** `voss/harness/tools.py:77-97`

`make_toolset(cwd, renderer=None, net=None, session_id=None)` binds tools to a project cwd. Follow this pattern for a lazy service closure:

```python
service = None
def _code_service():
    nonlocal service
    if service is None:
        from .code.service import CodeIntelService
        service = CodeIntelService.for_cwd(cwd, session_id=session_id)
    return service
```

Keep imports lazy inside `make_toolset()` so default installs and simple tests do not import pygls/ast-grep paths unless a code tool is used.

**Analog:** `voss/harness/tools.py:343-369`

`fs_grep()` shows the local read-only search style:

```python
try:
    rx = re.compile(pattern)
except re.error as e:
    return f"<error: bad regex: {e}>"
hits: list[str] = []
...
if len(hits) >= 200:
    break
return "\n".join(hits) if hits else "<no matches>"
```

Adapt: M10 should return structured JSON-ish text/envelopes, but keep the same bounded, no-crash behavior for bad patterns and unreadable files.

**Analog:** `voss/harness/tools.py:443-469`

Register code tools adjacent to other read-only tools:

```python
"fs_grep": ToolEntry(descriptor=fs_grep, is_mutating=False),
...
"voss_check": ToolEntry(descriptor=voss_check, is_mutating=False),
```

Add:

- `code_search`
- `find_definition`
- `find_references`
- `code_refresh`

All four are `is_mutating=False`. Do not set `is_network=True`.

### 2. Slash Commands

**Analog:** `voss/harness/slash.py:11-18`

Slash command shape is a frozen dataclass with handler and mutating flag:

```python
@dataclass(frozen=True)
class SlashCommand:
    name: str
    help: str
    handler: SlashHandler
    aliases: tuple[str, ...] = ()
    mutating: bool = False
    hidden: bool = False
```

`/symbol`, `/refs`, and `/refresh` should be registered in `cli.py:_build_slash_registry()`, not in `slash.py`.

**Analog:** `voss/harness/cli.py:573-964`

Existing slash handlers are local nested functions inside `_build_slash_registry()`, then registered in one tuple. Copy this style. Handler output uses `click.echo(...)`; handler errors print usage to `err=True`.

Useful existing handler patterns:

- `cli.py:787-790` `/tools` reads `ctx.tools` and prints stable lines.
- `cli.py:791-795` `/analyze` delegates to a service/registry.
- `cli.py:757-785` `/resume` validates args and reports a usage string on missing args.

For M10:

- `/symbol <name>`: parse args, call code service from `ctx` or lazily construct from `ctx.cwd`.
- `/refs <symbol>`: same.
- `/refresh [paths...]`: call `code_refresh`; although it writes cache, SPEC says the harness tool is read-only from user project perspective. Slash `mutating` should be decided by planner, but avoid permission prompts unless M10 deliberately classifies cache writes as mutating.

**Analog:** `voss/harness/cli.py:1687-1734`

Grouped help has explicit buckets and an "Other" fallback. Add code-intel commands to an existing group or a new "Code" group; otherwise they land under Other, which is allowed but less intentional.

**Tests:** `tests/e2e/test_slash_matrix.py:13-15` says adding a slash requires adding a row. `test_slash_registry_matches_test_matrix()` at `:63-85` fails on uncovered commands. Add rows for all three commands.

**Reserved names:** `voss/harness/tui/reserved_slash_names.py:13` locks only `("/recall", "/forget", "/memory", "/save")`. `/symbol`, `/refs`, `/refresh` do not collide. Keep that file unchanged.

### 3. Session Start, Context Loading, And System Prompt Injection

**Analog:** `voss/harness/cli.py:1327-1380`

`_run_repl()` constructs renderer/tools/registries, loads cognition, reads VOSS.md, then builds `ReplContext`:

```python
renderer = make_renderer(...)
tools = make_toolset(cwd, ..., session_id=record.id)
slash_registry = _build_slash_registry()
...
bundle = cognition_mod.load(cwd, token_count=_tok_count)
voss_md_text = voss_md.read_and_inject(cwd)
...
ctx = ReplContext(..., cognition=bundle, voss_md_text=voss_md_text, ...)
```

M10 session-start scan belongs in this boot area, after token-count helpers exist and before the first turn dispatch. The service/index summary needs to be available to both:

- `run_turn(..., project_index_text=...)` or equivalent
- TUI app state for `CodeIntelPanel`

Do not block slash registry construction on scan success. Scan failure should produce no context section and no traceback.

**Analog:** `voss/harness/agent.py:79-132`

`_compose_cognition_prompt()` shows bounded context rendering with graceful token-count fallback. Copy the pattern: pure renderer, optional token counter, never crash a turn because counting failed.

**Analog:** `voss/harness/agent.py:290-318`

`_compose_system_blocks()` keeps static prompt slices separate:

```python
blocks = [
    {"type": "text", "text": text}
    for text in (
        voss_md_block,
        cognition_text,
        prior_context_text,
        loop_system,
    )
    if text
]
if blocks:
    blocks[-1] = {**blocks[-1], "cache_control": {"type": "ephemeral"}}
```

Adapt by adding `project_index_text` as a separate block, likely after cognition and before prior context/loop system. Preserve the "last block gets cache_control" behavior.

**Analog:** `tests/harness/test_voss_md_injection.py:21-86`

The provider-capture test helper concatenates system message blocks whether `content` is a string or block list. Reuse this exact testing style for `## Project Index`.

### 4. Session Persistence And Redaction Boundaries

**Analog:** `voss/harness/session.py:13-34`

Session redaction is schema allowlisting, not arbitrary content scrubbing:

```text
SessionRecord is a fixed-field dataclass...
RunRecord follows the same fixed-field allowlist...
Adding a RunRecord field that could carry creds is a breaking change...
```

M10 must not add snippet payload fields to `SessionRecord` or `RunRecord`. Tool results already persist through iteration records, so code-intel snippets must be bounded before they become tool result text.

**Analog:** `voss/harness/agent.py:794-800`

Iteration tool results persist as:

```python
{
    "name": s.name,
    "args": telemetry.redact_tool_args(dict(s.args)),
    "result": str(r)[:4096],
}
```

This is a hard cap, but not semantic redaction. M10 should cap snippets earlier: 80 chars per line x 10 lines by default, then stringify. Auto-injected `## Project Index` must include no raw snippets.

**Analog:** `voss/harness/agent.py:1049-1131`

Tool invocation records telemetry and recorder output with result text:

```python
res = await entry.invoke(**step.args)
text = str(res)
...
recorder.observe(step.name, step.args, text, ok=True)
```

The recorder receives raw tool result text. Do not rely on `telemetry.redact_tool_args()` for result payloads; it only touches args. Bound and sanitize code-intel result strings inside the code-intel service.

**Analog:** `voss/harness/telemetry.py:105-120`

`redact_tool_args()` is shallow and key-based. Use it for args, but do not describe it as result redaction.

### 5. Cache Paths And Path Jailing

**Analog:** `.gitignore:9`

Project cache root is ignored:

```gitignore
.voss-cache/
```

**Analog:** `voss/harness/cognition.py:71-76`

Existing helpers distinguish durable state and cache:

```python
def voss_dir(cwd: Path) -> Path:
    return cwd / ".voss"

def cache_dir(cwd: Path) -> Path:
    return cwd / ".voss-cache"
```

Use `.voss-cache/code/index.db`, not `.voss/`, for the SQLite index.

**Analog:** `voss/harness/sandbox.py:29-40`

All user/config/DB-loaded paths must pass through `jail_path()`:

```python
p = Path(target)
if not p.is_absolute():
    p = cwd_real / p
p = p.resolve()
p.relative_to(cwd_real)
```

Apply this when:

- indexing files found by git/walk
- resolving tool `path` args
- reading paths stored in SQLite
- accepting `/refresh paths`

**Analog:** `voss/harness/sandbox.py:93-102`

For cache writes, copy atomic write shape:

```python
cache_root = jail_path(project_root, ".voss-cache")
cache_root.mkdir(parents=True, exist_ok=True)
target = jail_path(cache_root, relpath)
tmp = target.with_suffix(target.suffix + ".tmp")
tmp.write_text(text)
tmp.replace(target)
```

For SQLite, use the same jailed parent directory creation. SQLite writes are not temp-file text writes, but the path discipline still applies.

**Analog:** `voss/harness/cognition.py:304-363`

`build_repo_idx()` uses git-first discovery, then walk fallback:

```python
subprocess.run(["git", "ls-files"], cwd=str(cwd), timeout=10)
...
for p in cwd.rglob("*"):
    if p.is_file() and ".git" not in p.parts:
        file_paths.append(p)
```

M10 should reuse the git-first strategy but also prune vendored directories. The vendored set exists at `cognition.py:443`:

```python
_VENDORED = {"node_modules", ".venv", ".git", "dist", "build", "target", ".voss-cache"}
```

### 6. Config Loading

**Analog:** `voss/harness/mcp/config.py:1-12`

For `.voss/lsp.yml`, use the MCP config pattern: module docstring, pydantic models, strict extra rejection.

```python
import yaml
from pydantic import BaseModel, Field, ValidationError

STRICT = {"extra": "forbid"}
```

**Analog:** `voss/harness/mcp/config.py:19-30`

Model shape:

```python
class McpServerConfig(BaseModel):
    model_config = STRICT
    command: list[str]
    args: list[str] = Field(default_factory=list)
    timeout_s: float = 30.0
```

Adapt for M10:

- `command: str` or `list[str]` per final schema; CONTEXT says per-language `command` plus `args`.
- `args: list[str] = Field(default_factory=list)`
- `init_options: dict = Field(default_factory=dict)`
- `root_markers: list[str] = Field(default_factory=list)`
- `disabled: bool = False`
- top-level `default_max_results`, `scan_timeout_ms`, `partial_index_threshold_ms`.

**Analog:** `voss/harness/mcp/config.py:58-71`

Loader shape:

```python
path = cwd / ".voss" / "mcp.yml"
if not path.exists():
    return None
raw = yaml.safe_load(path.read_text()) or {}
return McpConfig.model_validate(raw)
```

For M10, load packaged defaults first, then overlay `.voss/lsp.yml`. Missing project file should not be an error.

**Tests:** `tests/harness/mcp/test_mcp_config.py:10-34` covers present/absent loader; `:37-70` covers env/cwd substitution. M10 may not need env substitution unless planner adds it. If it does, copy MCP substitution exactly.

### 7. Subprocess, LSP Lifecycle, And Orphan Prevention

**Analog:** `voss/harness/lifecycle.py:99-104`

There is already a general subprocess/session registry:

```python
def register_subprocess(proc: asyncio.subprocess.Process) -> None:
    _SUBPROCESSES.append(proc)

def register_session(session: object) -> None:
    _SESSIONS.append(session)
```

Prefer reusing/extending this for LSP server processes rather than creating a second process registry with different reap semantics.

**Analog:** `voss/harness/lifecycle.py:151-169`

Process tree signaling supports POSIX process groups and fallback methods:

```python
if os.name == "posix" and use_process_group:
    os.killpg(os.getpgid(proc.pid), sig)
elif sig == signal_mod.SIGKILL and hasattr(proc, "kill"):
    proc.kill()
elif hasattr(proc, "send_signal"):
    proc.send_signal(sig)
```

Use this idea for LSP servers if they may spawn child processes. Do not assume POSIX-only behavior.

**Analog:** `voss/harness/lifecycle.py:485-522`

`reap_all()` terminates, waits, kills on timeout, closes sessions, then reaps jobs. LSP registry should hook into this path via `register_subprocess()` or `register_session()` with `aclose()`.

**Analog:** `voss/harness/lifecycle.py:540-561`

An atexit hook exists. If LSP servers are registered with lifecycle, they get the same fallback cleanup.

**Analog:** `tests/harness/test_lifecycle.py:25-58`

Tests cover both terminate and SIGKILL fallback with real subprocesses. M10 should add analogous fake-server tests for LSP lifecycle and an optional orphan audit using `psutil`.

**Analog:** `voss/harness/cli.py:1547-1563`

`_run_repl()` has an explicit finally block for background jobs:

```python
try:
    from . import lifecycle
    asyncio.run(lifecycle.reap_jobs())
    ...
    active_session.unlink(missing_ok=True)
except Exception as exc:
    click.echo(f"job reap skipped: {exc}", err=True)
```

If LSP cleanup cannot be fully covered by `reap_all()`, add a similarly local, swallow-all cleanup path. Planner should prefer one lifecycle close path to avoid missed exits.

### 8. ast-grep And Regex Fallback

**Analog:** `voss/harness/tools.py:472-494`

`_shell_capture()` shows subprocess timeout and output cap:

```python
proc = await asyncio.create_subprocess_exec(...)
out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
...
if len(text) > SHELL_OUTPUT_CAP_BYTES:
    text = text[:SHELL_OUTPUT_CAP_BYTES] + ...
```

For `ast_grep.py`, do not route through `shell_allowed()` because `ast-grep` is a backend dependency, not a user shell command. But copy:

- direct argv list
- cwd binding
- timeout
- stdout/stderr merge or explicit stderr handling
- OSError -> structured unavailable result
- bounded output parsing

**Analog:** `voss/harness/tools.py:343-369`

Regex fallback should be a bounded search over jailed, indexed files. It should skip binary/unreadable files and return a source tag like `"regex-fallback"`.

**Telemetry pattern:** `voss/harness/lifecycle.py:185-198` and agent tool telemetry show `telemetry.emit(...)` is guarded by `telemetry.enabled()` or swallow-all try/except. Emit `code_search.fallback=regex` without making telemetry availability part of correctness.

### 9. LSP Client And Registry

**Rough analog only:** `voss/harness/mcp/client.py:216-235`

MCP client shows JSON message write/read validation:

```python
proc.stdin.write(json.dumps(msg, separators=(",", ":")).encode("utf-8") + b"\n")
line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
value = json.loads(line.decode("utf-8"))
```

Do not copy this for LSP framing unless the pygls spike fails. LSP uses Content-Length framing and pygls is the locked dependency. The analog is useful only for:

- timeout discipline
- process pipe error handling
- typed Voss exceptions
- never letting protocol errors crash the whole harness

**Pattern:** own the interface in Voss. `lsp.py` should expose Voss models (`DefinitionResult`, `ReferenceResult`, etc.), not pygls classes.

**Registry pattern:** `lsp_registry.py` should be session/cwd scoped:

- lazy launch per language
- singleton server per language per service/session
- missing command -> `{ "result": "lsp_unavailable", "language": ..., "fallback": ... }`
- shutdown on service close/session exit

### 10. TUI Side Panel And Renderer Boundary

**Analog:** `voss/harness/tui/app.py:258-264`

Region grid is:

```python
yield HeaderBar(id="header")
with Horizontal():
    yield TurnView(id="main")
    yield SideRegion(id="side")
yield StatusLine(id="status")
yield InputBar(id="input")
```

M9-08 should keep `#side` as the container and mount `CodeIntelPanel` inside it by default.

**Analog:** `voss/harness/tui/styles.tcss:35-41`

Current side panel is hidden by default:

```tcss
#side {
    width: 40%;
    min-width: 28;
    max-width: 50;
    display: none;
}
```

M10/M9-08 changes this contract: no-spawn default should show CodeIntelPanel. The planner must explicitly update tests that currently assert hidden side region, especially `tests/harness/tui/test_app_shell.py:24-25`.

**Analog:** `voss/harness/tui/app.py:163-185`

Current side-region lifecycle:

```python
def mount_subagent_panel(self, panel):
    side = self.query_one("#side")
    side.mount(panel)
    side.display = True
    side.styles.display = "block"

def collapse_subagent(...):
    ...
    if not list(side.query(SubAgentPanel)):
        side.display = False
        side.styles.display = "none"
```

Adapt to a state machine:

- default owner: `CodeIntelPanel`
- active spawn owner: `SubAgentPanel`
- collapse last spawn: restore CodeIntelPanel
- active `/symbol` or `/refs`: update CodeIntelPanel state; do not displace SubAgentPanel
- pin: suspend automatic owner changes until unpinned

**Analog:** `voss/harness/tui/widgets/sub_agent_panel.py:16-70`

Widget style:

- Textual `Vertical`
- `DEFAULT_CSS` colocated with the widget
- constructor stores simple state
- `compose()` yields child widgets
- mutator methods query child IDs and render untrusted text with `markup=False`

Use this for `CodeIntelPanel`, especially for excerpts and symbol names.

**Analog:** `voss/harness/tui/renderer.py:188-205`

Private renderer extensions are allowed without changing `Renderer` protocol:

```python
def show_subagent_start(...)
def show_subagent_progress(...)
def show_subagent_end(...)
```

Add private code-intel methods on `TextualRenderer` if needed, but do not add code-intel methods to `voss.harness.render.Renderer` unless the planner identifies a hard requirement. `tests/harness/tui/test_live_visualization.py:14-17` explicitly checks subagent private methods are not on the protocol; preserve that philosophy.

**Tests:** `tests/harness/tui/test_live_visualization.py:25-49` shows side-panel mount/unmount structural tests. Copy this style for `CodeIntelPanel` and precedence tests.

### 11. Optional Extras And Package Data

**Analog:** `pyproject.toml:26-35`

Existing optional extra:

```toml
[project.optional-dependencies]
search = [
    "chromadb>=0.5.0",
    "sentence-transformers>=2.7.0",
]
```

Add:

```toml
code = [
    "pygls>=2.1,<3",
    "ast-grep-cli>=0.42,<0.43",
]
```

Keep default dependencies unchanged unless M10 deliberately chooses to make pygls mandatory. Research recommends optional.

**Analog:** `pyproject.toml:60-66`

Package data currently includes grammar/templates/agent files:

```toml
[tool.setuptools.package-data]
voss = [
    "grammar.lark",
    "py.typed",
    "templates/init/*",
    "harness/agent/*.voss",
]
```

Add `harness/code/defaults/*.yml` if defaults are loaded from package data.

### 12. Test Patterns And Gates

**Tool count gate:** `tests/harness/test_tools.py:110-115` pins counts:

```python
assert sum(1 for e in tools.values() if e.is_mutating) == 7
assert sum(1 for e in tools.values() if not e.is_mutating) == 10
```

M10 adds four read-only tools; update non-mutating count to 14 unless MCP dynamic tools alter the test context.

**Explicit read-only list:** `tests/harness/test_tools.py:81-92` enumerates read-only tools. Add the four code tools.

**Permission model:** `voss/harness/permissions.py:49-65` already allows all non-mutating tools in plan/edit/auto:

```python
if mode == "plan":
    if is_mutating:
        return False, "denied by mode plan"
    return True, "ok"
```

Do not add code-tool names to `READ_ONLY` unless needed for prompt behavior tests; the structural `is_mutating=False` path is the real authority.

**Runtime baseline gate:** `tests/harness/tui/test_no_new_runtime_hooks.py:20-25` pins:

- `voss/harness/recorder.py`
- `voss_runtime/probable.py`
- `voss_runtime/budget.py`
- `voss_runtime/agent.py`

M10 should not touch or update the hash baseline.

**Memory class gate:** `tests/harness/test_memory_runtime_reuse.py:20-46` forbids `class *Memory` under `voss/harness/`. Do not name any M10 class `CodeMemory` or similar.

## Shared Patterns

1. **Additive, lazy surfaces.** M10 should be a new `voss/harness/code/` package plus thin hooks in `tools.py`, `cli.py`, `agent.py`, and TUI. Avoid moving existing cognition, session, or permission logic.

2. **Cache vs durable state.** `.voss/` is durable project policy/config. `.voss-cache/` is rebuildable machine state. Therefore `.voss/lsp.yml` is durable config, while `.voss-cache/code/index.db` is disposable.

3. **Git-first file discovery.** Use `git ls-files` when available, fallback to `cwd.rglob("*")`, prune vendored directories, and jail all paths.

4. **Read-only semantics.** Code-intel tools read source and write only rebuildable cache. In harness permission terms they are non-mutating.

5. **Soft dependency contracts.** Missing ast-grep or missing language servers return structured fallback results. They must not leak `ImportError`, `FileNotFoundError`, or raw traceback text to the agent.

6. **Bounded output everywhere.** Tool results, slash output, TUI excerpts, and prompt injection must be bounded independently. System context includes counts/modules only, not source snippets.

7. **Renderer protocol restraint.** Use `TextualRenderer` private methods and app mutators for panel integration. Keep the cross-renderer `Renderer` protocol stable unless there is no alternative.

8. **Swallow noncritical boot failures.** Existing cognition drift checks, renderer methods, lifecycle cleanup, and MCP boot all avoid crashing the user path over noncritical support features. M10 scan/context failures should follow that pattern.

9. **Tests use temp dirs and fakes.** Default tests must not require real language servers, network, or downloads. Real LSP/ast-grep acceptance can be optional/skipped unless the `voss[code]` job installs them.

## No Analog Found

| Concern | Why no strong analog exists | Planner implication |
|---|---|---|
| SQLite symbol index | Repo has no `sqlite3` usage or `.db` schema code | Plan a small new schema module with explicit migration/rebuild-on-version-mismatch tests |
| pygls client-mode adapter | Existing MCP client is JSON-line JSON-RPC, not LSP Content-Length framing, and research says pygls client docs are thin | Include an early spike/fake server test; hide pygls behind Voss-owned adapter |
| ast-grep JSON stream parser | Existing search is regex-only and subprocess capture is whole-output | Add parser unit tests for JSONL, malformed rows, max-results truncation, timeout |
| Symbol ambiguity resolution | Current tools do not rank symbols or resolve name -> position -> definition/reference | Planner must define `ambiguous` result envelope instead of guessing |
| Partial index warning | Existing cognition load is synchronous and either loaded/errors; no partial-index state exists | Planner must define first-turn budget behavior and warning surface |
| CodeIntelPanel default side ownership | Current M9 side region is hidden unless SubAgentPanel exists | M9-08 must redefine `#side` default and update layout tests |
| Pin/unpin side-region behavior | No existing TUI pin state machine | M9-08 needs a minimal explicit state enum/fields and tests |

## Key Constraints For Planner

1. **Wave 0 gate:** M10 execution must not start until M9-08 exists, passed plan-checker, and executed. M10 Wave 0 should verify this only.

2. **SPEC mismatch:** Patch M10-SPEC acceptance from `.voss-cache/code/index.json` to `.voss-cache/code/index.db` before implementation plans rely on it.

3. **No source snippets in auto-injection:** `## Project Index` may include counts, top modules, entry points, and truncation markers only.

4. **Snippet-bearing results must be bounded before persistence:** cap at service level, not after recorder/session storage.

5. **No recorder/runtime baseline edits:** Do not touch `voss/harness/recorder.py` or `voss_runtime/{probable,budget,agent}.py`.

6. **No new harness memory class:** Avoid class names ending in `Memory` under `voss/harness/`.

7. **No background watcher:** Session-start plus on-demand refresh only. Do not introduce file-watch infrastructure.

8. **No LSP refactor/edit features:** M10 is definition/references/workspace-symbol-ish lookup only. No completion, hover, diagnostics, code actions, rename, formatting, or edits.

9. **No silent pygls fallback:** If pygls client mode is unusable after spike, escalate before hand-rolled LSP.

10. **One cwd root:** No cross-repo or monorepo scan semantics in M10.

11. **Path safety:** Every path from CLI args, slash args, tool args, config, or SQLite must be normalized and jailed against `cwd`.

12. **Default tests remain hermetic:** fake LSP server and parser fixtures in default tests; real language servers and live ast-grep checks marked optional/acceptance/slow as appropriate.

13. **Tool count and slash matrix must be updated:** Adding four tools and three slash commands will fail pinned tests until test expectations are adjusted.

14. **TUI side-region test drift is expected:** Existing tests assume hidden `#side` when no spawn. M9-08 must update that contract to CodeIntelPanel-visible default.

15. **Optional dependency packaging:** Add `voss[code]` extra and package data for defaults without pulling pygls/ast-grep into default install unless planner chooses otherwise.

