# Phase V7: Engineering Manager Loop (supersedes O5) - Pattern Map

**Mapped:** 2026-06-06
**Files analyzed:** 2 (1 modify, 1 create)
**Analogs found:** 2 / 2

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/cli.py` | controller (CLI subcommand addition) | request-response + async-drive | `voss/harness/cli.py:3540` (`consensus_cmd`) + `voss/harness/cli.py:3782` (`team_check_cmd`) | exact |
| `tests/harness/test_team_run_cli.py` | test | request-response + sign-off prompt | `tests/harness/test_team_check_cli.py` + `tests/harness/em/conftest.py` | exact |

---

## Pattern Assignments

### `voss/harness/cli.py` — `@team_group.command("run")` addition

**Analogs:**
- `voss/harness/cli.py:3782` — `team_check_cmd` (team-file load, team group registration, `Path(cwd_str).resolve()` pattern)
- `voss/harness/cli.py:3540` — `consensus_cmd` (async-drive with `asyncio.run(...)` in a sync click command)

---

#### Subcommand registration pattern (lines 3777–3785, 3847–3878)

```python
# voss/harness/cli.py:3777
@click.group("team")
def team_group() -> None:
    """Inspect and validate the team cage (VTEAM-10)."""

@team_group.command("check")        # existing — V7 adds "run" alongside this
@click.argument("path", required=False, default=".voss/team.voss")
@click.option("--json", "json_mode", is_flag=True, help="Emit machine-readable JSON.")
def team_check_cmd(path: str, json_mode: bool) -> None:
    ...

# team_group is already in AGENT_COMMANDS at line 3877 — no registration change needed.
AGENT_COMMANDS = (
    ...
    team_group,    # cli.py:3877 — V7 adds no new top-level entry
)
```

**V7 applies:** register `@team_group.command("run")` directly below `team_check_cmd`, same indent level, same group.

---

#### Team-file load pattern (lines 3800–3816)

```python
# voss/harness/cli.py:3800–3816
p = Path(path)
if not p.is_file():
    _fail(f"team file not found: {path}")

src = p.read_text(encoding="utf-8")
program = parse(src if src.endswith("\n") else src + "\n", str(p))
team_decl = next(
    (d for d in program.body if isinstance(d, TeamDecl)), None
)
if team_decl is None:
    _fail(f"no team{{}} block in {path}")

try:
    config, _registry = compile_team(team_decl)
except VossTeamConfigError as e:
    _fail(str(e))
    return  # unreachable; _fail raises. keeps type-checker happy.
```

**V7 applies:** Mirror this pattern in `team_run_cmd` for the `.voss/team.voss` path; fall through to `_default_team_config()` when `p.is_file()` returns False (opposite branch from `_fail` — V7 takes the fallback path instead of erroring).

---

#### Async-drive pattern in sync click command (lines 3551, 3575)

```python
# voss/harness/cli.py:3551
cwd = Path(cwd_str).resolve()

# voss/harness/cli.py:3575
result = asyncio.run(run_critique(provider, cfg.default_model, constraints, diff_text))
```

**V7 applies:** Same `asyncio.run(...)` in the sync command body — `asyncio` imported at top of file (already present), or lazily inside the command body as other subcommands do. Do NOT use `_run_turn_cancellable` (that's for agent turns with SIGINT + Textual renderer — unrelated).

---

#### Output / error echo pattern (lines 3562, 3582)

```python
# voss/harness/cli.py:3562
click.echo(str(exc), err=True)
sys.exit(2)

# voss/harness/cli.py:3582
click.echo(text)
```

**V7 applies:** Use `click.echo(text)` for RunFinal summary output; `click.echo(str(exc), err=True)` + `sys.exit(2)` for error paths.

---

#### `_default_team_config()` helper — imports to replicate

The new helper lives immediately above `team_run_cmd` and mirrors the lazy-import style of other subcommands:

```python
# Pattern source: voss/harness/team.py:48 (DEFAULT_ROSTER) + tests/harness/em/conftest.py:14–21
from voss.harness.team import (
    BoardSpec,
    TeamCeiling,
    TeamConfig,
    TeamPolicy,
    subagent_spec_from_role,   # V3 function that applies role defaults
)
from voss.harness.subagents import SubagentRegistry
from voss.ast_nodes import Span
```

**V7 applies:** `_default_team_config()` is a module-level helper (not a click command). It builds `TeamConfig` + `SubagentRegistry` from `DEFAULT_ROSTER` without touching the parser. Use keyword `Span(file="<default>", line_start=0, col_start=0, line_end=0, col_end=0)` — positional order differs across Span versions.

---

#### `chmod 0o600` sidecar-write pattern (session_tree.py:97–102)

```python
# voss/harness/session_tree.py:97–102
def _write_node_file(node: SessionTreeNode, cwd: Path) -> Path:
    path = cwd / ".voss" / "sessions" / node.root_id / f"{node.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(node.to_dict(), indent=2))
    path.chmod(0o600)
    return path
```

**V7 applies:** `_persist_run_final` mirrors this exactly — same directory structure (`.voss/sessions/<root_id>/`), same `mkdir(parents=True, exist_ok=True)`, same `write_text(json.dumps(..., indent=2))`, same `chmod(0o600)`. Path derived from `rf.root_id` NEVER from user input.

---

#### Sign-off prompt pattern (click.prompt + Choice)

```python
# Pattern: RESEARCH.md Pattern 5 (verified against click CliRunner)
decision = click.prompt(
    "Sign off on this run",
    type=click.Choice(["approve", "reject"]),
)
```

**V7 applies:** Use `click.prompt` with `type=click.Choice([...])` — NOT `click.confirm`. This makes the CliRunner test pattern `input="approve\n"` / `input="reject\n"` deterministic with no branching.

---

### `tests/harness/test_team_run_cli.py` — new test file

**Analogs:**
- `tests/harness/test_team_check_cli.py` — CliRunner invocation pattern against `team` group, fixture for `root` group, `_write` helper, class-less test functions (V7 uses class-based per CONTEXT conventions — adapt structure)
- `tests/harness/em/conftest.py` — `stub_recorder` fixture (`SessionTreeNode.create_root` + `SessionTreeManager`), `tiny_team_config` fixture, `make_handle` factory, `DeterministicEMStub` scripted usage

---

#### CliRunner fixture and root-group setup (test_team_check_cli.py:36–40)

```python
# tests/harness/test_team_check_cli.py:36–40
import click
import pytest
from click.testing import CliRunner
from voss.harness import cli

@pytest.fixture()
def root() -> click.Group:
    g = click.Group("voss")
    cli.register(g)
    return g
```

**V7 applies:** Copy this `root` fixture verbatim into `test_team_run_cli.py`. All `CliRunner().invoke(root, ["team", "run", ...])` calls use it.

---

#### CliRunner invocation with input= for sign-off (test_team_check_cli.py + RESEARCH verification)

```python
# tests/harness/test_team_check_cli.py:53 (base invocation pattern)
res = CliRunner().invoke(root, ["team", "check", str(f)])
assert res.exit_code == 0, res.output

# V7 sign-off variant (RESEARCH.md Pattern 5, verified):
result = CliRunner().invoke(
    root,
    ["team", "run", "build API", "--cwd", str(tmp_path)],
    input="approve\n",
)
assert result.exit_code == 0
```

**V7 applies:** Use `input="approve\n"` / `input="reject\n"` in `TestSignOff` class tests. The `CliRunner` runs synchronously; `asyncio.run(...)` inside the command body works because there is no running event loop inside CliRunner.

---

#### `_write` helper for tmp_path team file (test_team_check_cli.py:43–48)

```python
# tests/harness/test_team_check_cli.py:43–48
def _write(tmp_path, src: str):
    d = tmp_path / ".voss"
    d.mkdir()
    f = d / "team.voss"
    f.write_text(src, encoding="utf-8")
    return f
```

**V7 applies:** Replicate this helper for tests exercising the team-file-present path (`test_team_file_override`). For the default-roster fallback tests, simply pass `--cwd` pointing to a `tmp_path` that has no `.voss/team.voss`.

---

#### EMBoardHandle fixture stack (tests/harness/em/conftest.py:79–135)

```python
# tests/harness/em/conftest.py:79–82
@pytest.fixture
def stub_recorder(tmp_path):
    root = SessionTreeNode.create_root(cwd=tmp_path, limit=1_000_000)
    manager = SessionTreeManager(root, reserve=0, cwd=tmp_path)
    return manager, tmp_path

# tests/harness/em/conftest.py:86–99
@pytest.fixture
def tiny_team_config():
    return TeamConfig(
        name="TestTeam",
        ceiling=TeamCeiling(
            budget_tokens=1_000_000,
            scope=TeamRoleScope(globs=("src/**",)),
            latency_seconds=600,
        ),
        policy=TeamPolicy(p=None),
        em_agent_id="em",
        roster_ids=frozenset({"backend", "frontend", "ai"}),
        board=BoardSpec(raw_items=()),
        rituals=(),
    )

# tests/harness/em/conftest.py:103–104
@pytest.fixture
def base_gate():
    return PermissionGate(mode="auto", auto_yes=True)
```

**V7 applies:** For `TestTeamRunCLI` integration tests that drive the full stack via CliRunner, the fixtures are implicit (CliRunner drives `_default_team_config()` internally). For `TestRunFinalPersist` unit tests that test `_persist_run_final` directly, replicate the `stub_recorder` pattern (SessionTreeNode.create_root + SessionTreeManager) in a local fixture.

---

#### DeterministicEMStub scripted usage (em/stub.py + test_em_loop.py:22–33)

```python
# tests/harness/em/test_em_loop.py:22–33
from voss.harness.em.schema import CreateTicketOp, EMPlanResponse, NoopOp
from voss.harness.em.stub import DeterministicEMStub

stub = DeterministicEMStub(scripted=[
    EMPlanResponse(ops=[
        CreateTicketOp(original_idea="Build API", worker_role="backend"),
    ], reasoning="planning"),
    EMPlanResponse(ops=[NoopOp(reason="waiting")], reasoning="idle"),
])
```

**V7 applies:** `TestTeamRunCLI` integration tests via CliRunner will use `DeterministicEMStub` injected through the CLI's stub path. For the CliRunner path, the stub is constructed inside the command body (since the command calls `_default_team_config()` then builds the stack). Tests that need to assert on stub behavior (e.g., `test_produces_card_and_run_final`) rely on the RunFinal output written to `run-final.json` — no direct stub reference needed in the test body.

---

#### pytest.mark.asyncio NOT needed for CliRunner tests (pitfall 4 from RESEARCH)

```python
# tests/harness/em/test_em_loop.py:17–18 — async em_loop tests use this:
@pytest.mark.asyncio
async def test_idea_to_done(self, make_handle, stub_board):

# V7 CliRunner tests do NOT use @pytest.mark.asyncio — they are sync:
class TestTeamRunCLI:
    def test_stub_run_exits_zero(self, root, tmp_path) -> None:
        result = CliRunner().invoke(root, ["team", "run", "build API",
                                           "--cwd", str(tmp_path)],
                                   input="approve\n")
        assert result.exit_code == 0, result.output
```

---

## Shared Patterns

### Lazy imports inside command body

**Source:** `voss/harness/cli.py:3787–3791` (`team_check_cmd`)
**Apply to:** `team_run_cmd`

```python
# voss/harness/cli.py:3787–3791
def team_check_cmd(path: str, json_mode: bool) -> None:
    """Validate a .voss team file via the compile_team validator."""
    import json as json_lib

    from voss import parse
    from voss.ast_nodes import TeamDecl
    from voss.harness.team import VossTeamConfigError, compile_team
```

All new imports for `team_run_cmd` should follow this lazy-import-inside-command-body convention. This avoids circular import risk at module load time and matches the project-wide CLI pattern.

---

### `Path(cwd_str).resolve()` as first action

**Source:** `voss/harness/cli.py:3551` (`consensus_cmd`)
**Apply to:** `team_run_cmd`

```python
cwd = Path(cwd_str).resolve()
```

Always resolve the cwd to an absolute path before passing to any harness component.

---

### `sys.exit(0)` / `sys.exit(1)` / `sys.exit(2)` exit conventions

**Source:** `voss/harness/cli.py:3556–3584`
**Apply to:** `team_run_cmd` error paths

```python
sys.exit(0)   # success / no-op
sys.exit(1)   # validation / config error
sys.exit(2)   # runtime / unexpected error
```

---

### RunFinal dataclass — do NOT access aspirational fields

**Source:** `voss/harness/em/tickets.py:111–131`
**Apply to:** `_persist_run_final`, `TestRunFinalPersist`

```python
@dataclass(frozen=True, slots=True)
class RunFinal:
    root_id: str
    idea: str
    total_cards: int
    done_count: int
    blocked_count: int
    killed_count: int
    rescope_count: int
    em_iterations: int
    ts: str
    kind: Literal["em.run_final"] = "em.run_final"
```

Exactly 10 fields. `evidence_refs`, `diff_summary`, `residual` do NOT exist. `dataclasses.asdict(rf)` gives the 10-field dict; sidecar adds `sign_off` as a superset key.

---

### Test acceptance gate

**Source:** `V7-RESEARCH.md §Validation Architecture`
**Apply to:** all V7 test commands

```
# Per-task gate:
.venv/bin/python -m pytest tests/harness/em/ -x -q

# Per-wave gate:
.venv/bin/python -m pytest tests/harness/em/ tests/harness/test_team_run_cli.py -q

# DO NOT include tests/harness/board/ — 13 pre-existing RED failures from V6 scaffolds
```

---

## No Analog Found

No files are entirely without analog. The `_persist_run_final` helper is new logic but follows the `_write_node_file` pattern from `session_tree.py:97–102` closely enough to count as a role-match.

| File / Component | Closest Reference | Notes |
|------------------|-------------------|-------|
| `_default_team_config()` helper | `voss/harness/team.py:48` (`DEFAULT_ROSTER`) + `tests/harness/em/conftest.py:86–99` (`tiny_team_config`) | No existing "build TeamConfig without parser" function — must construct directly |
| `_persist_run_final()` helper | `voss/harness/session_tree.py:97–102` (`_write_node_file`) | Pattern match: mkdir + write_text + chmod 0o600; path derived from `rf.root_id` |

---

## Metadata

**Analog search scope:** `voss/harness/cli.py`, `tests/harness/test_team_check_cli.py`, `tests/harness/em/conftest.py`, `tests/harness/em/test_em_loop.py`, `tests/harness/board/conftest.py`, `voss/harness/session_tree.py`, `voss/harness/em/tickets.py`, `voss/harness/em/loop.py`, `voss/harness/em/handle.py`, `voss/harness/em/stub.py`, `voss/harness/board/machine.py`, `voss/harness/team.py`
**Files scanned:** 12 (all read directly)
**Pattern extraction date:** 2026-06-06
