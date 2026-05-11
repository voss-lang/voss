# Phase M2: Project Cognition - Pattern Map

**Mapped:** 2026-05-10
**Files analyzed:** 19 (5 new modules, 6 modified modules, 5 new tests, 4 extended tests; minus 1 dep file = 19)
**Analogs found:** 19 / 19

Every M2 file has a direct M1 analog in the same repo. M2 is a pure extension of the M1 harness, so the closest analog is almost always the M1 sibling module the new code lives next to.

## File Classification

### New modules

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------------------------------|--------------------|---------------------|--------------------------------------|---------------|
| `voss/harness/cognition.py` | service (resolver) | request-response (pure) | `voss/harness/auth.py` (`resolve()`) | exact |
| `voss/harness/cognition_schemas.py` | model (config) | transform | `voss/harness/agent.py` (`Plan`) | role-match |
| `voss/harness/recorder.py` | service (observer) | event-driven | `voss/harness/permissions.py` (`PermissionGate`) | role-match |
| `voss/harness/skills/__init__.py` | package marker | — | `voss/harness/__init__.py` | exact |
| `voss/harness/skills/analyze.py` | controller (slash) | request-response | `voss/harness/cli.py:_run_repl` slash dispatch | role-match |

### Modified modules

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|----------------------------|--------------------|-----------------|--------------------------------------|---------------|
| `voss/harness/session.py` | model + service | CRUD | self (M1 baseline) | exact |
| `voss/harness/agent.py` | service (turn driver) | request-response | self (M1 baseline) | exact |
| `voss/harness/cli.py` | controller (CLI/REPL)| request-response | self (M1 baseline) | exact |
| `voss/harness/permissions.py` | middleware (gate) | request-response | self (M1 baseline) | exact |
| `voss/harness/tools.py` | model registry | event-driven | self (M1 baseline) | exact |
| `voss/harness/render.py` | view (renderer) | streaming/event | self (M1 baseline) | exact |

### New tests

| New Test | Role | Data Flow | Closest Analog | Match Quality |
|----------------------------------------------|-------|-----------|----------------------------------------------|---------------|
| `tests/harness/conftest.py` | fixture| — | `tests/harness/test_session.py:isolated_state` | role-match |
| `tests/harness/test_cognition.py` | test | unit+integ| `tests/harness/test_session.py` | role-match |
| `tests/harness/test_cognition_schemas.py` | test | unit | `tests/harness/test_sandbox.py` | role-match |
| `tests/harness/test_recorder.py` | test | unit | `tests/harness/test_tools.py` (tool obs)| role-match |
| `tests/harness/test_repl_cognition.py` | test | integration | `tests/harness/test_cli.py` (REPL flow) | role-match |

### Extended tests

| Extended Test | Role | Data Flow | Closest Analog | Match Quality |
|------------------------------------------|-------|------------------|----------------------------------------|---------------|
| `tests/harness/test_session.py` | test | unit | self | exact |
| `tests/harness/test_session_redaction.py`| test | unit (pattern scan) | self (M1-03 baseline; depends on M1) | exact |
| `tests/harness/test_cli.py` | test | integration | self | exact |
| `tests/harness/test_agent_integration.py`| test | integration | self | exact |

---

## Pattern Assignments

### `voss/harness/cognition.py` (service, request-response)

**Analog:** `voss/harness/auth.py` — pure resolver that returns a frozen dataclass.

**Imports + module docstring pattern** (auth.py:1-23):
```python
"""Credential discovery for Claude Code (Anthropic) and Codex (OpenAI).

Order of preference (when --auth=auto):
  1. Explicit env vars (ANTHROPIC_API_KEY / OPENAI_API_KEY)
  2. ...
"""
from __future__ import annotations

import json
import os
...
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
```

**Result dataclass pattern** (auth.py:279-285):
```python
@dataclass
class Resolution:
    source: str  # "env-anthropic" | "env-openai" | ...
    detail: str
    anthropic_oauth: Optional[AnthropicOAuthCreds] = None
    ...
```
Copy this shape for `CognitionBundle` (and `ArchitectureFrontmatter`, `DriftStatus`) — frozen dataclasses with optional sub-bundles, no methods other than `__post_init__`.

**Pure resolver function pattern** (auth.py:288-329):
```python
def resolve(preference: str = "auto") -> Resolution:
    """Decide which auth path to use.

    preference: auto | claude | codex | api | none
    """
    if preference == "none":
        return Resolution(source="none", detail="forced none")
    if preference in ("auto", "api"):
        if k := os.environ.get("ANTHROPIC_API_KEY"):
            return Resolution(source="env-anthropic", detail="ANTHROPIC_API_KEY", ...)
        ...
```
Copy: pure function, no exceptions raised for "not configured" — return a sentinel state (`Resolution(source="none")` ⇔ `CognitionBundle(initialized=False)`). Errors are accumulated into a `load_errors: list[str]` field, never raised.

**Filesystem-state probe pattern** (auth.py uses `_read_macos_keychain` returning `Optional[dict]`; auth.py:61-78):
```python
def _read_macos_keychain() -> Optional[dict]:
    if platform.system() != "Darwin":
        return None
    try:
        out = subprocess.run(["security", "find-generic-password", ...], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except json.JSONDecodeError:
        return None
```
Apply to `_git_rev_list_count`, `_git_ls_files_count`, `_load_yaml`, `_load_arch` — wrap subprocess + parse in try/except, return `None` on failure, push a string into `errors: list[str]` rather than raising.

**Drift-detection git subprocess** — same shape as `cli.py:_git_status` (cli.py:80-99):
```python
def _git_status(cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return "not a git repo"
    if out.returncode != 0:
        return "not a git repo"
```
Reuse for `git rev-list --count <sha>..HEAD`, `git rev-parse HEAD`, `git ls-files | wc -l`. Pitfall 4 in RESEARCH (force-rebase) handled by the same `returncode != 0` check.

---

### `voss/harness/cognition_schemas.py` (model, transform)

**Analog:** `voss/harness/agent.py` (the `Plan` / `ToolCall` pydantic models).

**Imports + strict-model pattern** (agent.py:14-15, 35-56):
```python
from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    name: str = Field(description="Tool name from the available tool list.")
    args: dict[str, Any] = Field(default_factory=dict, description="Keyword arguments.")
    why: str = Field(default="", description="One-line rationale for this call.")


class Plan(BaseModel):
    rationale: str = Field(description="One-paragraph reasoning for the chosen approach.")
    steps: list[ToolCall] = Field(default_factory=list, description="Sequential tool calls.")
    confidence: float = Field(ge=0.0, le=1.0, description="...")
    open_question: str | None = Field(default=None, description="...")
```
Copy: pydantic v2 `BaseModel`, `Field(...)` with `description=`, `default_factory=list`, numeric bounds (`ge=`, `le=`).

**Strictness extension (M2-specific, from RESEARCH Pattern 2):**
```python
STRICT = {"extra": "forbid"}   # M1's Plan does NOT use this; M2 adds it.

class ConstraintRule(BaseModel):
    model_config = STRICT
    forbid: list[str] | None = None
    require_tests_for: list[str] | None = None
    max_file_size_lines: int | None = Field(default=None, gt=0)
    custom: str | None = None
```
Rationale for the divergence: `Plan` is LLM output (lenient OK); cognition YAML is human/agent-authored config that must fail loud per D-07.

**Loud-error helper pattern** — no existing direct analog in voss/harness; mirror pydantic's `loc_to_dot_sep` from research Pattern 2:
```python
def _loc(loc: tuple) -> str:
    return ".".join(str(x) for x in loc) or "<root>"

def parse_constraints(path: Path) -> tuple[ConstraintsConfig | None, list[str]]:
    try:
        raw = yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        return None, [f"{path}: invalid YAML: {e}"]
    try:
        return ConstraintsConfig.model_validate(raw), []
    except ValidationError as e:
        return None, [f"{path}: {_loc(err['loc'])}: {err['msg']}" for err in e.errors()]
```
Apply this 4x: `parse_constraints`, `parse_permissions`, `parse_validation`, `parse_project_meta`.

---

### `voss/harness/recorder.py` (service, event-driven)

**Analog:** `voss/harness/permissions.py:PermissionGate` — dataclass observer that participates in every tool call. Same lifetime (one per `run_turn`), same observer shape.

**Imports + module docstring pattern** (permissions.py:1-9):
```python
"""Permission gate for tool calls.

Modes:
- plan : reads auto, every write/shell prompts
- ...
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
```

**Tool-classification constant pattern** (permissions.py:21-23):
```python
READ_ONLY = {"fs_read", "fs_glob", "fs_grep", "git_status", "git_diff", "voss_check"}
WRITE = {"fs_write", "fs_edit"}
SHELL = {"shell_run"}
```
Copy directly for `RunRecorder`:
```python
INSPECT_TOOLS = {"fs_read", "fs_glob", "fs_grep"}
CHANGE_TOOLS = {"fs_write", "fs_edit"}
VALIDATE_TOOLS = {"shell_run", "voss_check"}
```
NOTE: these sets must stay in sync with `permissions.py` constants. Same module-top placement.

**Observer-as-dataclass pattern** (permissions.py:67-82):
```python
@dataclass
class PermissionGate:
    mode: Mode = "edit"
    store: PermissionStore | None = None
    auto_yes: bool = False
    prompt_fn = None

    def needs_prompt(self, tool_name: str) -> bool:
        ...

    def check(self, tool_name: str, args: dict) -> tuple[bool, str]:
        """Return (allowed, reason)."""
        ...
```
Copy the dataclass-with-method shape for `RunRecorder` (RESEARCH Pattern 3 fills in fields). Single primary method `observe(tool_name, args, result, ok)` mirrors `check`; secondary `finalize(cwd, cost_usd) -> RunRecord`.

**Result-text parsing pattern** — the `shell_run` tool's output format `[exit N]\n<text>` (tools.py:58):
```python
return f"[exit {proc.returncode}]\n{text}"
```
Recorder's `_parse_exit(result)` MUST match this format precisely. Test by feeding a literal `tools.shell_run` result through the recorder.

**Git diff stat at turn end** — same subprocess shape as `cli.py:_git_status` (lines 82-99 above).

---

### `voss/harness/skills/analyze.py` (controller, request-response)

**Analog:** the slash-command dispatch block in `voss/harness/cli.py:_run_repl` (the `if line.startswith("/save")` branch is the closest existing analog for "slash command runs project-mutating logic and prints summary").

**Slash-command dispatch pattern** (cli.py:262-303):
```python
        if line in ("/exit", "/quit"):
            return
        if line == "/help":
            _print_slash_help()
            continue
        if line.startswith("/save"):
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip():
                record.name = parts[1].strip()
            record.total_cost_usd = total_cost
            record.model = cfg.default_model
            path = session_store.save(record, history)
            click.echo(f"saved: {path}")
            continue
```
Copy: `if line == "/analyze":` branch in `_run_repl`, then delegate to `skills.analyze.run(...)` which orchestrates the bootstrap prompt + `run_turn` + post-step `repo.idx` rebuild + `.gitignore` append. Print a one-line summary via `click.echo(f"cognition initialized: ...")`.

**Help-text registration pattern** (cli.py:372-386):
```python
def _print_slash_help() -> None:
    click.echo(
        "\n".join(
            [
                "/help          show this list",
                ...
                "/save [name]   persist session snapshot",
            ]
        )
    )
```
Add `"/analyze       refresh project cognition (.voss/, .voss-cache/)"` line.

**Bootstrap prompt → run_turn pattern** — `cli.py:do_cmd` builds a task string and calls `asyncio.run(run_turn(...))` (cli.py:166-176). Mirror that:
```python
result = asyncio.run(
    run_turn(
        bootstrap_prompt,           # crafted in skills/analyze.py
        tools=tools,
        cwd=cwd,
        renderer=renderer,
        model=cfg.default_model,
        provider=provider,
        permissions=gate,
        cognition=None,             # M2-NEW: skip auto-inject for bootstrap turn
    )
)
```

---

### `voss/harness/session.py` (MODIFIED — model + service, CRUD)

**Analog:** itself (M1 baseline). Pattern preservation is the point.

**Module docstring + redaction guarantee pattern** (session.py:1-6, plus M1-03 extension):
```python
"""Persisted session snapshots.

Sessions live at $XDG_STATE_HOME/voss/sessions/<id>.json (default
~/.local/state/voss/sessions). ...
"""
```
M2 rewrites this to describe the per-cwd path AND extends the M1-03 "Redaction guarantee" stanza to cover `RunRecord` fields. Verbatim from M1-03 plan:
```
Redaction guarantee
-------------------
SessionRecord is a fixed-field dataclass. Save serializes via dataclasses.asdict,
which means nothing outside the schema gets written. Provider credentials
(API keys, OAuth access/refresh tokens, Bearer headers, anthropic-beta marker)
are NEVER fields on this record and therefore cannot be saved.
```
M2 adds: "RunRecord follows the same fixed-field allowlist. New fields are a breaking change to the redaction contract."

**State-dir resolution pattern** (session.py:20-22):
```python
def _state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "voss" / "sessions"
```
M2 replaces with two functions:
```python
def _sessions_dir(cwd: Path) -> Path:
    return (cwd / ".voss" / "sessions").resolve()

def _legacy_state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "voss" / "sessions"
```
Same env-var fallback for legacy reads (D-12).

**Dataclass schema-allowlist pattern** (session.py:25-34):
```python
@dataclass
class SessionRecord:
    id: str
    name: str
    cwd: str
    model: str
    started_at: str
    updated_at: str
    total_cost_usd: float = 0.0
    turns: list[dict] = field(default_factory=list)
```
M2 adds **one** field — `runs: list[dict] = field(default_factory=list)` — at end. Preserve `asdict(record)` serialization in `save()` so no extra fields can leak.

`RunRecord` is itself a `@dataclass` (not pydantic) to inherit this same schema-allowlist invariant (RESEARCH "Standard Stack > Alternatives Considered" explicitly chose dataclass over BaseModel for this reason).

**Save pattern with 0600 chmod** (session.py:60-67):
```python
def save(record: SessionRecord, history: EpisodicMemory) -> Path:
    record.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    record.turns = history.last(10_000)
    path = session_path(record.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(record), indent=2))
    path.chmod(0o600)
    return path
```
Preserve verbatim except: `session_path(record.id)` now uses `_sessions_dir(Path(record.cwd))` instead of `_state_dir()`. `0o600` chmod stays.

**Backward-compat load pattern** (session.py:86):
```python
record = SessionRecord(**{k: v for k, v in data.items() if k != "turns"}, turns=data.get("turns", []))
```
M2 must extend this for legacy sessions missing `runs`:
```python
known = {k: v for k, v in data.items() if k in _SESSION_FIELDS}
known.setdefault("turns", [])
known.setdefault("runs", [])     # NEW for M2 backward-compat
record = SessionRecord(**known)
```
RESEARCH Pitfall 7 calls this out explicitly.

---

### `voss/harness/agent.py` (MODIFIED — service, request-response)

**Analog:** itself (M1 baseline).

**Cognition prepend at turn start** — insert just before `renderer.show_thinking("planning")` (agent.py:149). Current line:
```python
    user_prompt = (
        f"Task:\n{task}\n\n"
        f"Working directory: {cwd}\n\n"
        f"Available tools:\n{_format_tools(tools)}{history_block}\n"
    )

    if history is not None:
        history.add(task, role="user")

    renderer.show_thinking("planning")
    async with ContextScope(...):
        resp = await provider.complete(
            messages=[
                {"role": "system", "content": PLAN_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            ...
        )
```
M2 modifies the system message construction to prepend cognition (D-17). Use a `_compose_cognition_prompt(cognition)` helper that takes the `CognitionBundle` and returns the prepended block, then concatenates with `\n\n` + `PLAN_SYSTEM`. The `messages=[...]` shape stays identical.

**Tool dispatch loop pattern** (agent.py:185-207):
```python
    gate = permissions or PermissionGate(auto_yes=True)
    results: list[str] = []
    for i, step in enumerate(plan.steps):
        td = tools.get(step.name)
        if td is None:
            results.append(f"<error: unknown tool {step.name!r}>")
            renderer.show_tool_call(step.name, step.args, "<unknown tool>", "error")
            continue
        allowed, why = gate.check(step.name, step.args)
        if not allowed:
            text = f"<denied: {why}>"
            renderer.show_tool_call(step.name, step.args, text, "error")
            results.append(text)
            continue
        renderer.show_tool_call(step.name, step.args, "running…", "pending")
        try:
            res = await td.invoke(**step.args)
            text = str(res)
        except Exception as e:  # noqa: BLE001
            text = f"<error: {e}>"
            renderer.show_tool_call(step.name, step.args, text, "error")
            results.append(text)
            continue
        renderer.show_tool_call(step.name, step.args, _summarize(text), "ok")
        results.append(text)
```
M2 adds `rec.observe(step.name, step.args, text, ok=True/False)` after each branch's final `results.append(...)`. Five insertion points: unknown-tool, denied, error, exception, ok. `RunRecorder.observe` is the only added line per branch.

**TurnResult pattern** (agent.py:82-88):
```python
@dataclass
class TurnResult:
    plan: Plan
    confidence: float
    final: str
    tool_results: list[str]
    cost_usd: float
```
M2 adds `run: RunRecord | None = None` field at end. Default `None` preserves the M1 `--auth=none` early-return path.

**Privileged closing call pattern** — no direct M1 analog. Use the same `provider.complete(messages=..., response_format=Model, ...)` shape as the main plan call (agent.py:152-162):
```python
resp = await provider.complete(
    messages=[
        {"role": "system", "content": PLAN_SYSTEM},
        {"role": "user", "content": user_prompt},
    ],
    model=model,
    response_format=Plan,
    temperature=0.2,
    max_tokens=cfg.max_output_tokens,
)
```
Mirror with `response_format=RunSemantics`, `temperature=0.0`, `max_tokens=800`. Wrap in try/except — on any exception or `resp.parsed is None`, persist mechanical-only RunRecord with `goal="(record_run failed)"` per RESEARCH Pitfall 1.

---

### `voss/harness/cli.py` (MODIFIED — controller, request-response)

**Analog:** itself.

**Slash-command branch pattern** (cli.py:262-303 — already extracted above for `skills/analyze.py`).
Add a new branch:
```python
        if line == "/analyze":
            from .skills.analyze import run as analyze_run
            analyze_run(cwd=cwd, provider=provider, history=history,
                        record=record, renderer=renderer, tools=tools, gate=gate)
            continue
```
Insertion order: after `/save`, before the catch-all `if line.startswith("/")`.

**Click command + flag pattern** (cli.py:389-399, the existing `sessions_cmd`):
```python
@click.command("sessions")
def sessions_cmd() -> None:
    """List saved agent sessions."""
    records = session_store.list_sessions()
    if not records:
        click.echo("(no sessions)")
        return
    for r in records:
        click.echo(
            f"  {r.id[:8]}  {r.updated_at}  {r.model:<28}  {r.first_task()}"
        )
```
M2 adds `--all` / `--global` flag using the same `@click.option` shape used elsewhere (e.g. `cli.py:118` `@click.option("--yes", "yes_to_all", is_flag=True, ...)`):
```python
@click.command("sessions")
@click.option("--all", "--global", "include_legacy", is_flag=True,
              help="Include legacy sessions from ~/.local/state/voss/sessions/.")
def sessions_cmd(include_legacy: bool) -> None:
    cwd = Path.cwd()
    records = session_store.list_sessions(cwd=cwd, include_legacy=include_legacy)
    ...
    for r in records:
        tag = "[legacy] " if getattr(r, "_legacy", False) else ""
        click.echo(f"  {tag}{r.id[:8]} ...")
```

**Doctor row pattern** (cli.py:333-369):
```python
@click.command("doctor")
def doctor_cmd() -> None:
    """Diagnose env: credentials, runtime imports, picked auth path."""
    cfg = get_config()
    click.echo(f"default model       : {cfg.default_model}")
    click.echo(f"ANTHROPIC_API_KEY   : {'set' if os.environ.get('ANTHROPIC_API_KEY') else 'unset'}")
    ...
    claude = auth_mod.load_anthropic_oauth()
    if claude:
        click.echo(f"Claude Code OAuth   : found ({claude.subscription_type}, expires in {claude.expires_in_seconds}s)")
    else:
        click.echo("Claude Code OAuth   : not found")
```
M2 appends three rows using identical `f"{label:<20}: {value}"` layout (20-char left-padded label, colon-space, value):
```python
bundle = cognition.load(cwd)
click.echo(f".voss/ initialized  : {'yes' if bundle.initialized else 'no'}")
if bundle.initialized and bundle.architecture_frontmatter:
    drift = cognition.drift_check(cwd, bundle.architecture_frontmatter)
    click.echo(f"cognition staleness : {'stale (' + drift.reason + ')' if drift.is_stale else 'fresh'}")
legacy_count = len(list(session_store._legacy_state_dir().glob("*.json")))
if legacy_count:
    click.echo(f"legacy sessions     : {legacy_count} (read-only via voss sessions --all)")
```
Same "diagnose, don't fix" stance (M1 D-13).

**Drift hint at REPL start** — modeled on `cli.py:248-249`:
```python
    if record.turns:
        click.echo(f"resumed: {record.name} ({len(record.turns)} prior turns)")
```
Add similarly minimal:
```python
    bundle = cognition.load(cwd, token_count=lambda t: litellm.token_counter(model=cfg.default_model, text=t))
    if bundle.initialized and bundle.architecture_frontmatter:
        drift = cognition.drift_check(cwd, bundle.architecture_frontmatter)
        if drift.is_stale:
            click.echo(f"  [dim]cognition stale ({drift.reason}) — /analyze to refresh[/dim]")
    if bundle.load_errors:
        for err in bundle.load_errors:
            click.echo(f"  [yellow]cognition error:[/yellow] {err}", err=True)
```

---

### `voss/harness/permissions.py` (MODIFIED — middleware, request-response)

**Analog:** itself.

**Layering pattern** — M2 adds project-level rules from `.voss/permissions.yml` on top of the M1 session-scoped gate. Current `PermissionGate.check` (permissions.py:89-97):
```python
def check(self, tool_name: str, args: dict) -> tuple[bool, str]:
    """Return (allowed, reason)."""
    if not self.needs_prompt(tool_name):
        return True, "auto"
    if self.store is not None:
        sig = self.signature(tool_name, args)
        if sig in self.store.always:
            return True, "remembered"
    return self._prompt(tool_name, args)
```
M2 inserts a new clause **first** (deny-wins-over-allow per RESEARCH Open Question 3):
```python
def check(self, tool_name: str, args: dict) -> tuple[bool, str]:
    """Return (allowed, reason).

    Project-level deny from .voss/permissions.yml always wins.
    Project-level allow is additive but cannot expand session-mode permissions.
    """
    if self.project_policy:
        if tool_name in self.project_policy.tool_policy.deny:
            return False, "denied by .voss/permissions.yml"
    if not self.needs_prompt(tool_name):
        return True, "auto"
    ...
```
Add `project_policy: PermissionsConfig | None = None` field on the dataclass; loaded from `cognition.load(cwd).permissions` at REPL boot.

---

### `voss/harness/tools.py` (MODIFIED — model registry, event-driven)

**Analog:** itself, plus `voss_runtime.tools.ToolDescriptor` (the dataclass at `voss_runtime/tools.py:41-62`).

**Tool factory pattern** (tools.py:13-149):
```python
def make_toolset(cwd: Path) -> dict[str, Any]:
    """Build the harness toolset bound to a project cwd."""

    @tool(name="fs_write", description="Write text to a file inside cwd. ...")
    async def fs_write(path: str, content: str) -> str:
        p = jail_path(cwd, path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
        return f"wrote {len(content)} bytes to {path}"

    return {
        "fs_read": fs_read,
        ...
        "fs_write": fs_write,
        ...
    }
```
**ASSUMPTION:** M1 CONTEXT.md and M2 CONTEXT.md cite `is_mutating: bool` as an M1 tool descriptor field. The actual `voss_runtime/tools.py:ToolDescriptor` (lines 41-62) does NOT currently have it. M1-05 introduces it. M2 plans should `depends_on: [M1-05]` for the `record_run` tool descriptor.

**`record_run` privileged tool registration** — there is NO direct M1 analog because `record_run` is dispatched by the harness, not picked by the LLM (D-15 + RESEARCH Pattern 4). It still gets a descriptor for symmetry. Modeled on `voss_check` (tools.py:131-137) since it's a small purposeful tool:
```python
@tool(
    name="record_run",
    description="(privileged) Close the current turn with semantic fields. Dispatched by the harness.",
)
async def record_run(goal: str, avoided: list = [], assumptions: list = [],
                     decisions: list = [], risks: list = [], follow_ups: list = []) -> str:
    return "ok"
```
The descriptor exists so `tools.py:make_toolset` can expose it consistently, but `_run_repl`/`run_turn` never put `record_run` in `plan.steps`. Mark `is_mutating=True` when M1-05 lands.

---

### `voss/harness/render.py` (MODIFIED — view, streaming)

**Analog:** itself.

**Renderer protocol pattern** (render.py:24-32):
```python
class Renderer(Protocol):
    def banner(self, *, model: str, cwd: Path, git_status: str) -> None: ...
    def show_user(self, task: str) -> None: ...
    def show_thinking(self, label: str) -> None: ...
    def show_plan(self, plan: Any, *, cost_usd: float) -> None: ...
    def show_tool_call(self, name: str, args: dict, summary: str, state: str) -> None: ...
    def show_clarify(self, question: str, confidence: float) -> None: ...
    def show_final(self, text: str, *, confidence: float, cost_usd: float) -> None: ...
    def status(self, *, model: str, tokens: int, cost_usd: float, ctx_pct: float) -> None: ...
```
M2 adds one method to the Protocol:
```python
    def show_cognition(self, *, architecture_tokens: int, constraints_count: int,
                       plans_loaded: int = 0, decisions_loaded: int = 0) -> None: ...
```
Each of Tty/Plain/Json must implement it.

**Tty dim-line pattern** (render.py:70-71):
```python
def show_thinking(self, label: str) -> None:
    self.console.print(f"[dim]  … {label}[/dim]")
```
Copy directly:
```python
def show_cognition(self, *, architecture_tokens, constraints_count, plans_loaded=0, decisions_loaded=0):
    arch_k = architecture_tokens / 1000
    self.console.print(
        f"[dim]  cognition: architecture ({arch_k:.1f}k) + {constraints_count} constraints[/dim]"
    )
```
Suppress when `--quiet` per D-20.

**Plain renderer pattern** (render.py:134-159) — each method either no-ops or prints to `sys.stderr`:
```python
def show_thinking(self, label: str) -> None:
    print(f"... {label}", file=sys.stderr)
```
`show_cognition` follows: `print(f"cognition: arch={architecture_tokens}tok constraints={constraints_count}", file=sys.stderr)`.

**JSON event pattern** (render.py:170-203):
```python
class JsonRenderer:
    V = 1

    def _emit(self, **kw: Any) -> None:
        kw.setdefault("v", self.V)
        sys.stdout.write(json.dumps(kw, default=str) + "\n")
        sys.stdout.flush()

    def show_thinking(self, label: str) -> None:
        self._emit(type="thinking", label=label)
```
Copy directly:
```python
def show_cognition(self, *, architecture_tokens, constraints_count, plans_loaded=0, decisions_loaded=0):
    self._emit(type="cognition_loaded",
               architecture_tokens=architecture_tokens,
               constraints_count=constraints_count,
               plans_loaded=plans_loaded,
               decisions_loaded=decisions_loaded)
```
Also add `_emit(type="cognition_overflow", architecture_tokens=N, budget=6000)` for D-18 overflow.

---

### `tests/harness/conftest.py` (NEW — fixture)

**Analog:** the inline `isolated_state` fixture in `tests/harness/test_session.py:11-14`:
```python
@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path
```
Promote to `conftest.py` and add `git_repo` fixture for drift tests (RESEARCH Wave 0 Gaps):
```python
@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("# t\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=tmp_path, check=True, capture_output=True)
    return tmp_path
```

---

### `tests/harness/test_cognition.py` (NEW — unit/integration)

**Analog:** `tests/harness/test_session.py` — class-based test layout with one round-trip class per concern.

**Class-based test pattern** (test_session.py:17-30):
```python
class TestSessionRoundtrip:
    def test_save_then_list(self, tmp_path: Path) -> None:
        history = EpisodicMemory(capacity=20)
        history.add("rename foo to bar", role="user")
        ...
        rec = ss.SessionRecord.new(cwd=tmp_path, model="claude-sonnet-4-5")
        rec.total_cost_usd = 0.012
        path = ss.save(rec, history)
        assert path.exists()
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        sessions = ss.list_sessions()
        assert len(sessions) == 1
        assert sessions[0].id == rec.id
```
Mirror with `TestCognitionLoad`, `TestDriftCheck`, `TestArchitectureFrontmatter`, `TestRepoIdx`, `TestGitignoreIdempotent`, `TestFilenameCollision`, `TestDecisionFrontmatter`. One assertion class per RESEARCH §"Phase Requirements → Test Map" group.

---

### `tests/harness/test_cognition_schemas.py` (NEW — unit)

**Analog:** `tests/harness/test_sandbox.py` (small focused unit tests on a single module's API surface).

```python
# Mirror test_sandbox.py:
class TestConstraintsConfig:
    def test_extra_forbid_rejects_unknown_key(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ConstraintsConfig.model_validate({"rules": [], "stray_key": 1})

    def test_max_file_size_lines_must_be_positive(self) -> None:
        with pytest.raises(ValidationError):
            ConstraintRule.model_validate({"max_file_size_lines": 0})
```
RESEARCH §"Validation Architecture" enumerates the exact assertions to add.

---

### `tests/harness/test_recorder.py` (NEW — unit)

**Analog:** `tests/harness/test_tools.py` for the tool-side, plus `tests/harness/test_agent_integration.py:FakeProvider` for the wider end-to-end.

**Mechanical-capture test pattern:**
```python
class TestRunRecorder:
    def test_inspect_captures_fs_read(self) -> None:
        rec = RunRecorder.start()
        rec.observe("fs_read", {"path": "a.py"}, "contents", ok=True)
        assert "a.py" in rec.inspected

    def test_validation_captures_exit_code(self) -> None:
        rec = RunRecorder.start()
        rec.observe("shell_run", {"cmd": "pytest"}, "[exit 1]\nfailed", ok=True)
        assert rec.validation[0]["exit"] == 1
```
The `[exit N]\n…` string format MUST match `voss/harness/tools.py:58` verbatim — that's the contract.

---

### `tests/harness/test_repl_cognition.py` (NEW — integration)

**Analog:** `tests/harness/test_cli.py` uses `CliRunner` from click for REPL/CLI flows:
```python
from click.testing import CliRunner
from voss.harness.cli import main

class TestCli:
    def test_help(self) -> None:
        r = CliRunner().invoke(main, ["--help"])
        assert r.exit_code == 0
        assert "voss" in r.output
```
Drift, status-line, NDJSON event tests use this same `CliRunner` shape. Combine with the `git_repo` fixture from conftest.py.

---

### `tests/harness/test_session_redaction.py` (EXTENDED — unit pattern scan)

**Analog:** the M1-03 plan body (not yet a file; M2 extends what M1-03 ships).

**Pattern scan extension** — M1-03 plan §"Task 1" Test 4:
```python
SECRET_PATTERNS = ["Authorization", "Bearer ", "sk-ant-", "sk-proj-", "oauth_token", "access_token"]

def test_run_record_no_secret_patterns(tmp_path):
    rec = SessionRecord.new(cwd=tmp_path, model="m")
    rec.runs = [asdict(RunRecord(id="t1", started_at="t0", ended_at="t1",
                                  goal="clean goal", inspected=["src/a.py"]))]
    save(rec, EpisodicMemory(capacity=4))
    text = session_path(rec.id).read_text()
    for pat in SECRET_PATTERNS:
        assert pat not in text, f"redaction leak: {pat!r} found in session JSON"
```

**Top-level keys allowlist test:**
```python
def test_run_record_top_level_keys():
    expected = {"id", "started_at", "ended_at", "goal", "plan", "inspected", "changed",
                "avoided", "assumptions", "decisions", "risks", "validation", "failures",
                "diff_summary", "follow_ups", "cost_usd"}
    rec = asdict(RunRecord(id="t", started_at="t0", ended_at="t1"))
    assert set(rec.keys()) == expected
```
Locks the 16-field schema (CONTEXT.md D-14; note: 16 keys, not 17 — the spec has goal+inspected+changed+avoided+assumptions+decisions+risks+validation+failures+diff_summary+follow_ups+cost_usd+plan+id+started_at+ended_at = 16. RESEARCH §"Phase Requirements" cites "17 declared keys" — verify count when writing).

---

### `tests/harness/test_agent_integration.py` (EXTENDED — integration)

**Analog:** itself. Existing `FakeProvider` (test_agent_integration.py:21-53) returns a canned `Plan`. M2 extends to return canned `RunSemantics` on the second `provider.complete` call:
```python
class FakeProviderWithSemantics(FakeProvider):
    def __init__(self, plan: Plan, semantics: RunSemantics, cost: float = 0.001):
        super().__init__(plan, cost)
        self.semantics = semantics
        self._call_count = 0

    async def complete(self, *, messages, model, response_format=None, **kw):
        self._call_count += 1
        if response_format is RunSemantics:
            return ProviderResponse(text=self.semantics.model_dump_json(),
                                    model=model, prompt_tokens=20, completion_tokens=80,
                                    cost_usd=0.0001, raw={}, parsed=self.semantics)
        return await super().complete(messages=messages, model=model,
                                       response_format=response_format, **kw)
```
Use for `test_record_run_populates_semantic_fields`, `test_record_run_failure_persists_mechanical`, `test_turn_injects_cognition`, `test_resume_injects_prior_run_context`.

---

## Shared Patterns

### Schema-allowlist redaction
**Source:** `voss/harness/session.py` (`@dataclass SessionRecord` + `asdict(record)` serialization) + M1-03 redaction test pattern.
**Apply to:** `RunRecord` (in session.py), the `runs: list[dict]` field on `SessionRecord`, the `decisions/*.md` frontmatter writer.
```python
@dataclass
class RunRecord:
    id: str
    started_at: str
    ended_at: str
    goal: str = ""
    plan: dict | None = None
    # ... fixed list per D-14 ...
```
Concrete: NO `**kwargs`, NO `extra` field, NO `metadata: dict` field that could swallow secrets. Every new value is a named field. Test `test_run_record_top_level_keys` enforces this.

### Loud-fail config parse
**Source:** RESEARCH Pattern 2 + `voss/harness/auth.py` pattern of returning `None` on failure rather than raising.
**Apply to:** Every `.voss/*.yml` parse in `cognition.py`.
Concrete: `parse_X(path) -> tuple[Model | None, list[str]]`. Errors get joined into `CognitionBundle.load_errors`. `_run_repl` prints all errors at boot, never raises mid-turn. Drift check follows the same shape.

### Subprocess wrap (git + shell)
**Source:** `voss/harness/cli.py:_git_status` (lines 80-99) and `voss/harness/tools.py:_shell_capture` (lines 152-170).
**Apply to:** Every git call in `cognition.py` (`git rev-parse HEAD`, `git rev-list --count`, `git ls-files`, `git diff --stat`). RunRecorder's `_git_diff_stat`.
Concrete: try/except `(OSError, subprocess.SubprocessError)` (cli pattern) OR `asyncio.create_subprocess_exec` + `asyncio.wait_for(timeout=30.0)` (tools pattern). Non-async sites use the cli pattern; async sites use the tools pattern. NEVER let a subprocess error raise into a renderer.

### Sandbox jail for all writes
**Source:** `voss/harness/sandbox.py:jail_path` (lines 20-31).
**Apply to:** Every `.voss/` and `.voss-cache/` write path through agent tools (already covered — agent uses `fs_write` which already jails). New `cognition.py` writes (`.voss-cache/repo.idx`, `.voss/.gitignore` autogen) MUST also use `jail_path(cwd, ".voss-cache/repo.idx")` even though they're harness-direct.
```python
def jail_path(cwd: Path, target: str | os.PathLike) -> Path:
    cwd_real = cwd.resolve()
    p = Path(target)
    if not p.is_absolute():
        p = cwd_real / p
    p = p.resolve()
    try:
        p.relative_to(cwd_real)
    except ValueError as e:
        raise SandboxError(f"path escapes cwd: {p}") from e
    return p
```
Use verbatim. RESEARCH §"Security Domain" "Symlink in .voss/" mitigation.

### Slash-command registry
**Source:** `voss/harness/cli.py:_run_repl` lines 262-303 (the chain of `if line ==/startswith` branches).
**Apply to:** `/analyze` (new), `/help` text registration, plus any future cognition slash.
Concrete shape:
```python
if line == "/analyze":
    from .skills.analyze import run as analyze_run
    analyze_run(cwd=cwd, ...)
    continue
```
No registry data structure — keep the M1 chain-of-if pattern. Adding `/analyze` to `_print_slash_help` is one extra string literal.

### Renderer trio extension
**Source:** `voss/harness/render.py` — every event added to `Renderer` Protocol gets three implementations (Tty rich-dim line, Plain stderr print, Json `_emit(type=...)`).
**Apply to:** `show_cognition`. Also any new event added by drift detection or overflow.

### Click flag pattern
**Source:** `voss/harness/cli.py:118` (`@click.option("--yes", "yes_to_all", is_flag=True, help="...")`).
**Apply to:** `sessions --all` / `--global` (alias via second name on the same `click.option`).
```python
@click.option("--all", "--global", "include_legacy", is_flag=True,
              help="Include legacy sessions from ~/.local/state/voss/sessions/.")
```

### Backward-compat dataclass load
**Source:** `voss/harness/session.py:86` — explicit `{k: v for k, v in data.items() if k != "turns"}, turns=data.get("turns", [])`.
**Apply to:** Loading legacy sessions missing `runs` (RESEARCH Pitfall 7). New helper:
```python
_SESSION_FIELDS = {f.name for f in dataclasses.fields(SessionRecord)}

def _hydrate(data: dict) -> SessionRecord:
    kept = {k: v for k, v in data.items() if k in _SESSION_FIELDS}
    kept.setdefault("turns", [])
    kept.setdefault("runs", [])
    return SessionRecord(**kept)
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | Every M2 file mirrors an M1 file. The `record_run` privileged closing dispatch has no direct M1 analog (no prior code makes a follow-up LLM call after a turn) — but the LLM-call shape itself is copied from `run_turn`'s primary `provider.complete(...)` call, so this is "role-match analog", not "no analog". |

The only genuinely-new shape is the cross-cutting cognition bundle threading (parameter passes from `cli._run_repl` → `agent.run_turn` → renderer), but that is the M1 `permissions: PermissionGate | None = None` pattern applied to a second collaborator. Cite `permissions` thread-through in `agent.py:111` and `cli.py:174` as the analog.

---

## Metadata

**Analog search scope:** `voss/harness/**`, `voss_runtime/**`, `tests/harness/**`. Skipped `voss/compiler/**` (unrelated), `voss/runtime/**` (only `voss_runtime` aliased package matters), `site/**` (Next.js, unrelated to harness).
**Files scanned:** 12 source files + 7 test files.
**Pattern extraction date:** 2026-05-10
**Cross-references checked:** M1-CONTEXT.md (D-15 session move deferred), M1-03 plan (redaction test pattern), M1-CLI patterns (slash registry), `voss_runtime/tools.py:ToolDescriptor` (note: `is_mutating` is M1-05, not yet landed — planner MUST sequence M2 after M1).

**Open assumption flagged for planner:**
- `ToolDescriptor.is_mutating: bool` does not exist in current `voss_runtime/tools.py`. CONTEXT.md and RESEARCH.md treat it as M1 baseline (per M1-05). M2 plans referencing `is_mutating` must declare `depends_on: M1-05` or include the field-add as part of their plan.
