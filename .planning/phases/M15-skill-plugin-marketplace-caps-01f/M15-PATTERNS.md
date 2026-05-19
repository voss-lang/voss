# Phase M15: Skill / Plugin Marketplace (CAPS-01f) - Pattern Map

**Mapped:** 2026-05-19
**Files analyzed:** 12 new/modified files
**Analogs found:** 11 / 12

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/plugins.py` (extend) | service | file-I/O + CRUD | `voss/harness/plugins.py` itself | self (extension) |
| `voss/harness/skill_registry.py` (extend) | service | CRUD + event-driven | `voss/harness/skill_registry.py` itself | self (extension) |
| `voss/harness/trust.py` (new) | utility | file-I/O + transform | `voss/harness/permissions.py` | role-match |
| `voss/harness/cli.py` (extend `skill`/`plugin` groups) | controller | request-response | `voss/harness/cli.py` `skill_group`/`plugin_group` | self (extension) |
| `voss/cli.py` (extend `voss skill install/publish`) | controller | request-response | `voss/cli.py` `run` command | role-match |
| `voss/harness/recorder.py` (extend events) | service | event-driven | `voss/harness/recorder.py` itself | self (extension) |
| `voss/harness/mcp/server_skills.py` (adapt `.voss` dispatch) | middleware | request-response | `voss/harness/mcp/server_skills.py` itself | self (extension) |
| `tests/harness/skill/test_install.py` (new) | test | CRUD | `tests/harness/test_extensions.py` | exact |
| `tests/harness/skill/test_trust.py` (new) | test | transform | `tests/harness/test_permissions.py` | role-match |
| `tests/harness/skill/test_dispatch.py` (new) | test | event-driven | `tests/skills/test_skills_smoke.py` | exact |
| `tests/harness/skill/conftest.py` (new) | test | — | `tests/skills/conftest.py` | exact |
| `examples/skills/` bundle (new .voss files) | config | file-I/O | `voss/harness/skills/voss/summarize-diff.voss` | exact |

---

## Pattern Assignments

### `voss/harness/plugins.py` — extend with `install_skill` / `uninstall_skill` / trust-aware loading

**Analog:** `voss/harness/plugins.py` (self-extension)

**Imports pattern** (lines 1-13):
```python
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

try:
    import tomli_w
except Exception:  # noqa: BLE001
    tomli_w = None  # type: ignore[assignment]
```

**Directory convention** (lines 28-34):
```python
def user_plugin_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "plugins"

def project_plugin_dir(cwd: Path) -> Path:
    return cwd / ".voss" / "plugins"
```

**Enablement persistence pattern** (lines 60-77) — copy for `install_skill` writing a `.toml`:
```python
def set_plugin_enabled(plugin_id: str, enabled: bool) -> Path:
    path = enablement_path()
    current = _load_enablement()
    current[plugin_id] = enabled
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"plugins": {k: {"enabled": v} for k, v in sorted(current.items())}}
    if tomli_w is not None:
        text = tomli_w.dumps(payload)
    else:
        lines: list[str] = []
        for key, value in payload["plugins"].items():
            lines.append(f"[plugins.{key}]")
            lines.append(f"enabled = {'true' if value['enabled'] else 'false'}")
            lines.append("")
        text = "\n".join(lines)
    path.write_text(text)
    path.chmod(0o600)
    return path
```

**Manifest parsing / validation pattern** (lines 86-134) — copy `_read_manifest` shape for trust-annotated manifest parsing. New manifest fields `trust_level` and `signature` slot in after existing field reads (line 103 region):
```python
def _read_manifest(
    path: Path,
    *,
    command_ids: set[str],
    skill_ids: set[str],
    agent_ids: set[str],
    enabled_overrides: dict[str, bool],
) -> PluginManifest | None:
    try:
        raw = tomllib.loads(path.read_text())
    except (OSError, tomllib.TOMLDecodeError):
        return None
    plugin_id = str(raw.get("id", "")).strip()
    if not plugin_id:
        return None
    # ... field extraction ...
    enabled = enabled_overrides.get(plugin_id, bool(raw.get("enabled", False)))
    return PluginManifest(...)
```

**load_plugins scan pattern** (lines 137-160):
```python
def load_plugins(
    cwd: Path,
    *,
    command_ids: Iterable[str] = (),
    skill_ids: Iterable[str] = (),
    agent_ids: Iterable[str] = (),
) -> list[PluginManifest]:
    enabled_overrides = _load_enablement()
    manifests: list[PluginManifest] = []
    ids = (set(command_ids), set(skill_ids), set(agent_ids))
    for root in (project_plugin_dir(cwd), user_plugin_dir()):
        if not root.exists():
            continue
        for path in sorted(root.glob("*.toml")):
            manifest = _read_manifest(path, ...)
            if manifest is not None:
                manifests.append(manifest)
    return manifests
```

---

### `voss/harness/skill_registry.py` — extend with `.voss` dispatch adapter

**Analog:** `voss/harness/skill_registry.py` (self-extension)

**SkillEntry dataclass** (lines 10-15):
```python
@dataclass(frozen=True)
class SkillEntry:
    id: str
    description: str
    handler: SkillHandler
    mutating: bool = False
```

**Registry registration pattern** (lines 18-32):
```python
class SkillRegistry:
    def __init__(self) -> None:
        self._entries: dict[str, SkillEntry] = {}

    def register(self, entry: SkillEntry) -> None:
        self._entries[entry.id] = entry

    def get(self, skill_id: str) -> SkillEntry | None:
        return self._entries.get(skill_id)
```

**Handler signature** — all existing skill handlers use this exact shape (lines 38-49, 60-73, etc.):
```python
def handler_name(ctx: Any, args: list[str]) -> None:
    from .skills.module_name import run

    run(
        cwd=ctx.cwd,
        provider=ctx.provider,
        history=ctx.history,
        record=ctx.record,
        renderer=ctx.renderer,
        tools=ctx.tools,
        gate=ctx.gate,
        args=args,
    )
```

**`.voss` dispatch adapter pattern** — new `voss_dispatch_handler` wraps `voss run` subprocess (mirroring `voss/cli.py` `run` command lines 220-265). The handler compiles `.voss` to temp dir then executes via `subprocess.run([sys.executable, str(generated)])`:
```python
# From voss/cli.py lines 232-265 — the voss run subprocess pattern:
with tempfile.TemporaryDirectory(prefix="voss-run-") as tmp:
    tmp_dir = Path(tmp)
    generated = tmp_dir / (source.stem + ".py")
    _compile_source(source, output_path=generated, ...)
    completed = subprocess.run(
        [sys.executable, str(generated)],
        capture_output=True,
        text=True,
        env=env,
    )
    if completed.stdout:
        click.echo(completed.stdout, nl=False)
    if completed.stderr:
        click.echo(completed.stderr, nl=False, err=True)
```

---

### `voss/harness/trust.py` — new Ed25519 trust/signature module

**Analog:** `voss/harness/permissions.py` (role-match: same pattern of dataclass + load/save + check returning `(bool, str)`)

**No exact analog exists** for Ed25519 verification — see "No Analog Found" section. Use the structural pattern from `permissions.py`:

**Dataclass + load/save pattern** (permissions.py lines 109-142):
```python
@dataclass
class PermissionStore:
    cwd: Path
    always: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, cwd: Path) -> "PermissionStore":
        p = _config_path()
        if not p.exists():
            return cls(cwd=cwd)
        try:
            data = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError):
            return cls(cwd=cwd)
        ...

    def save(self) -> None:
        p = _config_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        ...
        p.write_text(json.dumps(data, indent=2))
```

**Check returning `(bool, str)` pattern** (permissions.py lines 172-197):
```python
def check(
    self,
    tool_name: str,
    args: dict,
    *,
    is_mutating: bool = False,
    is_network: bool = False,
) -> tuple[bool, str]:
    allowed, why = self._check_impl(...)
    return allowed, why
```

**Config path convention** (permissions.py lines 68-70):
```python
def _config_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "voss" / "permissions.json"
```

`trust.py` follows: `return base / "voss" / "trusted_keys.json"`.

**Error swallowing on I/O** (permissions.py lines 118-127) — all load paths use `except (OSError, json.JSONDecodeError): return cls(...)`. Trust module copies this: signature verification failure returns `(False, "signature invalid")`, never raises.

---

### `voss/harness/cli.py` — extend `skill_group` with `install`/`publish`/`search` subcommands

**Analog:** `voss/harness/cli.py` `skill_group` and `plugin_group` (self-extension, lines 2355-2416)

**Group + subcommand pattern** (lines 2363-2379):
```python
@click.group("plugin")
def plugin_group() -> None:
    """Manage plugin manifest enablement."""

@plugin_group.command("enable")
@click.argument("plugin_id")
def plugin_enable_cmd(plugin_id: str) -> None:
    path = set_plugin_enabled(plugin_id, True)
    click.echo(f"plugin {plugin_id} enabled: {path}")

@plugin_group.command("disable")
@click.argument("plugin_id")
def plugin_disable_cmd(plugin_id: str) -> None:
    path = set_plugin_enabled(plugin_id, False)
    click.echo(f"plugin {plugin_id} disabled: {path}")
```

**skill_run_cmd signature** (lines 2394-2415) — `install`/`publish` commands copy this option set:
```python
@skill_group.command("run")
@click.argument("skill_id")
@click.argument("args", nargs=-1)
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
@click.option("--model", default=None)
@click.option("--auth", "auth_pref", type=click.Choice(AUTH_CHOICES), default="auto")
def skill_run_cmd(
    skill_id: str,
    args: tuple[str, ...],
    cwd_str: str,
    model: str | None,
    auth_pref: str,
) -> None:
    """Run a registered skill."""
    cwd = Path(cwd_str).resolve()
    _resolve_default_model(model)
    _res, provider = _resolve_auth_or_die(auth_pref)
    ctx = _extension_context(cwd=cwd, provider=provider)
    entry = ctx.skill_registry.get(skill_id)
    if entry is None:
        raise click.ClickException(f"unknown skill: {skill_id}")
    entry.handler(ctx, list(args))
```

**AGENT_COMMANDS registration** (lines 2878-2908) — new subcommands added to `skill_group` auto-register; the `register()` function requires no changes:
```python
AGENT_COMMANDS = (
    ...
    skill_group,   # install/publish/search added as skill_group subcommands
    ...
)

def register(group: click.Group) -> None:
    for cmd in AGENT_COMMANDS:
        group.add_command(cmd)
```

---

### `voss/cli.py` — extend with `voss skill install` / `voss skill publish` top-level delegation

**Analog:** `voss/cli.py` `run` command (lines 220-265)

**Compile + subprocess dispatch pattern** (lines 84-140, 220-265):
```python
def _compile_source(
    source_path: Path,
    *,
    output_path: Path | None,
    project_root: Path | None,
    cache_dir: Path,
    verbose: bool = False,
) -> Path:
    if source_path.suffix != ".voss":
        raise click.ClickException(...)
    program = _parse_file(source_path)
    try:
        analysis = analyze(program, ...)
    except VossError as exc:
        raise click.ClickException(str(exc))
    ...
    _write_text_atomic(target, result.source)
    return target


@main.command("run")
@click.argument("source", type=click.Path(path_type=Path))
def run(source: Path, ...) -> None:
    with tempfile.TemporaryDirectory(prefix="voss-run-") as tmp:
        generated = tmp_dir / (source.stem + ".py")
        _compile_source(source, output_path=generated, ...)
        completed = subprocess.run(
            [sys.executable, str(generated)],
            capture_output=True, text=True, env=env,
        )
        if completed.stdout:
            click.echo(completed.stdout, nl=False)
        if completed.stderr:
            click.echo(completed.stderr, nl=False, err=True)
        raise click.exceptions.Exit(code=completed.returncode)
```

**Error exit pattern** (lines 261-265):
```python
raise click.exceptions.Exit(code=completed.returncode)
```

**Auth stub detection** (lines 242-253):
```python
hermetic_env_set = os.environ.get("VOSS_HERMETIC") == "1"
res = auth_mod.resolve(preference="auto")
should_stub = hermetic_env_set or res.source == "none"
if should_stub:
    click.echo("voss: no provider creds detected — using __stub__ ...", err=True)
    env = os.environ.copy()
    env["VOSS_HERMETIC"] = "1"
else:
    env = None
```

---

### `voss/harness/recorder.py` — extend with skill install/publish event types

**Analog:** `voss/harness/recorder.py` (self-extension)

**observe() dispatch pattern** (lines 56-81) — new event types `skill_install` / `skill_publish` slot into this method:
```python
def observe(self, tool_name: str, args: dict, result: Any, *, ok: bool) -> None:
    if not ok:
        self.failures.append(
            {"tool": tool_name, "error": str(result)[:FAILURE_TRUNC]}
        )
        return
    if tool_name in INSPECT_TOOLS:
        path = args.get("path") or args.get("pattern") or ""
        if path:
            self.inspected.append(path)
    elif tool_name in CHANGE_TOOLS:
        path = args.get("path", "")
        if path:
            self.changed.append(path)
    elif tool_name in VALIDATE_TOOLS:
        ...
        self.validation.append({...})
```

**Tool set constants pattern** (lines 20-23) — new constants follow same form:
```python
INSPECT_TOOLS = {"fs_read", "fs_glob", "fs_grep"}
CHANGE_TOOLS = {"fs_write", "fs_edit"}
VALIDATE_TOOLS = {"shell_run", "voss_check"}
# New:
# SKILL_EVENTS = {"skill_install", "skill_uninstall", "skill_publish"}
```

**finalize() aggregation** (lines 192-225) — new list fields added as `field(default_factory=list)` on the `RunRecorder` dataclass and forwarded to `RunRecord` in finalize exactly as `inspected`/`changed` are.

---

### `voss/harness/mcp/server_skills.py` — adapt `.voss` bundle dispatch

**Analog:** `voss/harness/mcp/server_skills.py` (self-extension)

**make_skill_dispatch factory pattern** (lines 27-64):
```python
def make_skill_dispatch(
    *,
    cwd: Path,
    provider,
    history,
    record,
    renderer,
    tools,
    gate,
    skill_registry,
) -> Callable[[str, list[str]], Awaitable[str]]:
    async def dispatch(name: str, args: list[str]) -> str:
        entry = skill_registry.get(name)
        if entry is None:
            raise KeyError(f"unknown skill: {name}")
        ctx = SimpleNamespace(
            cwd=cwd, provider=provider, history=history,
            record=record, renderer=renderer, tools=tools,
            gate=gate, skill_registry=skill_registry,
        )
        buf = io.StringIO()

        def _run() -> None:
            with contextlib.redirect_stdout(buf):
                entry.handler(ctx, list(args))

        await asyncio.to_thread(_run)
        return buf.getvalue()

    return dispatch
```

The `.voss` adapter extends this: when a `SkillEntry` has `source_type="voss"`, `_run` compiles the `.voss` file to a temp dir and execs it via subprocess instead of calling `entry.handler` directly. All other paths (gate, ctx construction, `asyncio.to_thread`) stay identical.

---

### `tests/harness/skill/conftest.py` — new test suite conftest

**Analog:** `tests/skills/conftest.py` (exact copy with adjustments)

**autouse isolated_state fixture** (lines 51-54):
```python
@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path
```

**FakeProvider class** (lines 85-157) — copy verbatim; downstream tests instantiate with their own `Plan` objects.

**seed_git_repo helper** (lines 57-77):
```python
def seed_git_repo(root: Path) -> Path:
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t"], ...)
    subprocess.run(["git", "config", "user.name", "t"], ...)
    if not (root / "README.md").exists():
        (root / "README.md").write_text("# t\n")
    subprocess.run(["git", "add", "."], ...)
    subprocess.run(["git", "commit", "-m", "init"], ...)
    return root
```

**Re-export pattern** (lines 34-48):
```python
__all__ = [
    "FakeProvider", "seed_git_repo", "Plan", "ToolCall", "run_turn",
    "PermissionGate", "PlainRenderer", "make_toolset",
    "Done", "ParsedPlan", "TextDelta", "Usage", "ProviderResponse",
]
```

---

### `tests/harness/skill/test_install.py` — CLI install/uninstall/list tests

**Analog:** `tests/harness/test_extensions.py` (exact match: CliRunner + plugin manifest pattern)

**CliRunner invocation pattern** (lines 112-122):
```python
def test_extension_cli_lists_builtins() -> None:
    runner = CliRunner()
    skills = runner.invoke(main, ["skills"])
    agents = runner.invoke(main, ["agents"])

    assert skills.exit_code == 0
    assert "analyze" in skills.output
```

**monkeypatch XDG + tmp plugin dir** (lines 76-109):
```python
def test_plugin_manifest_filters_unknown_refs_and_enablement(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    plugin_dir = tmp_path / ".voss" / "plugins"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "demo.toml").write_text(...)

    set_plugin_enabled("demo", True)
    plugins = load_plugins(tmp_path, ...)

    assert len(plugins) == 1
    assert plugin.enabled is True
```

---

### `tests/harness/skill/test_trust.py` — trust verification tests

**Analog:** `tests/harness/test_permissions.py` (role-match: dataclass check, `(bool, str)` returns)

**Gate check test structure** (test_permissions.py lines 64-80):
```python
@pytest.mark.asyncio
async def test_per_step_check_preserved_in_multi_step_read_batch() -> None:
    invocations: list[tuple[str, dict]] = []

    def _recorder(tool_name: str, args: dict, is_mutating: bool) -> tuple[bool, str]:
        invocations.append((tool_name, dict(args)))
        return True, "auto"

    gate = PermissionGate(auto_yes=True)
    original_check = gate.check
    def _wrapped(tool_name, args, *, is_mutating=False, is_network=False):
        _recorder(tool_name, args, is_mutating)
        return original_check(...)
```

For `test_trust.py`: trust check returns `(False, "signature invalid")` on bad key; `(True, "verified")` on valid. Pattern is identical `(bool, str)` tuple assertion.

---

### `tests/harness/skill/test_dispatch.py` — `.voss`-bundle dispatch tests

**Analog:** `tests/skills/test_skills_smoke.py` (exact: skill `run()` call with `FakeProvider` + gate assertions)

**Skill run + gate mode test pattern** (lines 43-81):
```python
def test_rename_symbol(tmp_path: Path) -> None:
    from voss.harness.skills.rename_symbol import run

    # (a) plan mode — zero mutations
    run(
        cwd=tmp_path, provider=None, history=None, record=None,
        renderer=PlainRenderer(), tools=make_toolset(tmp_path),
        gate=PermissionGate(mode="plan"), args=["foo", "bar"],
    )
    after_plan = {p.name: p.read_text() for p in tmp_path.glob("*.py")}
    assert after_plan == before, "plan mode mutated files — gate bypass"

    # (b) edit/auto — actual execution
    run(
        cwd=tmp_path, provider=None, history=None, record=None,
        renderer=PlainRenderer(), tools=make_toolset(tmp_path),
        gate=PermissionGate(auto_yes=True), args=["foo", "bar"],
    )
    entry = default_skill_registry().get("rename-symbol")
    assert entry is not None and entry.mutating is True
```

**FakeProvider + agentic skill pattern** (lines 128-163) — for `.voss` dispatch test, supply `FakeProvider(plan)` with a plan whose `final_when_done` carries the skill output text.

---

### `examples/skills/` — new `.voss` example bundles

**Analog:** `voss/harness/skills/voss/summarize-diff.voss` (exact)

**`.voss` dogfood skill structure** (summarize-diff.voss lines 1-12):
```voss
# skill-name.voss
# Commentary: NOT the runtime exec path — the skill is skills/module.py
# This file demonstrates the same flow in Voss and must pass `voss check`.
fn skillName(input: string) -> string {
    ctx(budget: 3000 tokens) {
        yield ask("...prompt...")
    }
}

let result = skillName("...example input...")
print(result)
```

Every new `.voss` example must:
1. Pass `voss check` (see `voss/cli.py` `check` command)
2. Have a companion `# NOT the runtime exec path` comment
3. Use `ctx(budget: N tokens)` for agentic work, bare `fn` for deterministic

---

## Shared Patterns

### Skill handler signature — apply to all new skill `run()` functions
**Source:** `voss/harness/skills/rename_symbol.py` lines 26-35 and `summarize_diff.py` lines 40-49
**Apply to:** All new `voss/harness/skills/*.py` files and `.voss`-dispatch wrappers
```python
def run(
    *,
    cwd: Path,
    provider,
    history,
    record,
    renderer,
    tools,
    gate,
    args: list[str] | None = None,  # omit when skill takes no args
) -> None:
```

### Gate self-enforcement for mutating skills
**Source:** `voss/harness/skills/rename_symbol.py` lines 63-72
**Apply to:** Any new skill with `mutating=True` that calls tools outside `run_turn`
```python
# Gate self-enforcement BEFORE any mutation (landmine #3 / Pitfall 2).
allowed, reason = gate.check(
    "fs_edit",
    {"path": rel, "old": old, "new": new},
    is_mutating=True,
)
if not allowed:
    click.echo(f"skill-name: {reason}", err=True)
    return
```

### PermissionGate `(bool, str)` return — apply to `trust.py` verify functions
**Source:** `voss/harness/permissions.py` lines 172-197
**Apply to:** `voss/harness/trust.py` all public verify functions
```python
def verify_manifest(manifest_path: Path, *, trusted_keys: set[str]) -> tuple[bool, str]:
    # returns (True, "verified") or (False, "reason string")
```

### TOML manifest I/O — apply to `plugins.py` install extension and new skill manifests
**Source:** `voss/harness/plugins.py` lines 86-134 (`_read_manifest`)
**Apply to:** `install_skill`, trust-aware load paths, example bundle manifests
```python
try:
    raw = tomllib.loads(path.read_text())
except (OSError, tomllib.TOMLDecodeError):
    return None  # never raise from manifest parsing
```

### Click group + subcommand registration pattern
**Source:** `voss/harness/cli.py` lines 2363-2379, 2878-2908
**Apply to:** All new `skill install` / `skill publish` / `skill search` subcommands
```python
@skill_group.command("install")
@click.argument("source")
@click.option("--trust", "trust_level", ...)
def skill_install_cmd(source: str, trust_level: str) -> None:
    ...

# Then add to AGENT_COMMANDS tuple — register() picks it up automatically
```

### XDG_CONFIG_HOME path convention — apply everywhere a config path is constructed
**Source:** `voss/harness/plugins.py` lines 28-30 / `permissions.py` lines 68-70
**Apply to:** `trust.py`, any new config helpers
```python
base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
return base / "voss" / "<filename>"
```

### Test isolation with monkeypatched XDG
**Source:** `tests/skills/conftest.py` lines 51-54 and `tests/harness/test_extensions.py` line 77
**Apply to:** All `tests/harness/skill/` test files
```python
monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
```

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `voss/harness/trust.py` (Ed25519 core) | utility | transform | No cryptographic signing/verification exists anywhere in the codebase. Use `PyNaCl` / `cryptography` library per RESEARCH.md. Structural pattern (dataclass + `(bool, str)` returns + XDG path) is borrowed from `permissions.py`. |

---

## Metadata

**Analog search scope:** `voss/harness/`, `voss/cli.py`, `tests/harness/`, `tests/skills/`, `voss/harness/mcp/`, `voss/harness/skills/`, `examples/`
**Files scanned:** 14 source files read in full
**Pattern extraction date:** 2026-05-19
