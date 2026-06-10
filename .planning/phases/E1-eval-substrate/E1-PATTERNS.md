# Phase E1: Eval Substrate - Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 9 (6 modified, 3 created)
**Analogs found:** 9 / 9

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/eval/suite.py` | model | transform | self (existing `TaskSpec`) | self-extension |
| `voss/eval/runner.py` | service | batch + request-response | self (existing `run_suite`) | self-extension |
| `voss/eval/judge.py` | service | request-response | self (existing `judge_run`) | self-extension |
| `voss/eval/summary.py` | utility | transform | self (existing `write_summary`) | self-extension |
| `voss/templates/eval/summary.md.jinja` | config | transform | self (existing jinja template) | self-extension |
| `voss/harness/cli.py` (eval_cmd) | controller | request-response | `voss/harness/cli.py` (any gated command) | role-match |
| `voss/harness/config.py` (new `[eval]` section) | config | CRUD | `voss/harness/config.py` `[agent]` section | exact |
| `tests/eval/conftest.py` | test | CRUD | `tests/harness/conftest.py` | role-match |
| `tests/eval/golden/*/task.toml` (6 files, retrofit) | config | transform | `tests/eval/golden/01-analyze/task.toml` | exact |

---

## Pattern Assignments

### `voss/eval/suite.py` — add `checks` discriminated-union field

**Analog:** `voss/eval/suite.py` (self), `voss/eval/judge.py` for `Literal` union pattern

**Existing imports/model pattern** (suite.py lines 1–9):
```python
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
```

**Existing `TaskSpec` shape** (suite.py lines 11–23) — new `checks` field slots in after `tools`:
```python
class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(description="Prompt passed to `voss do`.")
    mode: Literal["plan", "edit", "auto"]
    rubric: str = Field(description="Plain-text PASS/FAIL criteria (D-08).")
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    provider: str | None = None
    model: str | None = None
    auto_approve_edits: bool = False
    tools: list[str] = Field(default_factory=list)
    # NEW: checks: list[AnyCheck] = Field(default_factory=list)
```

**Discriminated-union pattern to copy from** (judge.py lines 12–19 — pydantic `Literal` discriminator shape):
```python
class Verdict(BaseModel):
    model_config = ConfigDict(extra="ignore")

    verdict: Literal["pass", "fail"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
```

**New check union — implement as (D-01)**:
```python
from typing import Annotated, Union
from pydantic import Discriminator, Tag

class CmdCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["cmd"]
    run: str
    timeout: int = 60

class FileExistsCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["file_exists"]
    path: str

class FileContainsCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: Literal["file_contains"]
    path: str
    text: str

AnyCheck = Annotated[
    Union[
        Annotated[CmdCheck, Tag("cmd")],
        Annotated[FileExistsCheck, Tag("file_exists")],
        Annotated[FileContainsCheck, Tag("file_contains")],
    ],
    Discriminator("type"),
]
```

**`TaskSpec.checks` field** — add at end of field list:
```python
checks: list[AnyCheck] = Field(default_factory=list)
```

**Back-compat invariant:** `load_task` unchanged — `tomllib` parses `[[checks]]` TOML array of tables naturally; pydantic validates via the new field.

---

### `voss/eval/runner.py` — check executor, turn cap, run-header print

**Analog:** `voss/eval/runner.py` (self) — slots into existing `run_suite` / `_drive_task` flow

**Existing imports** (runner.py lines 1–35) — add nothing new (all deps already present: `subprocess`, `time`, `Path`).

**Existing subprocess pattern for `_file_diff`** (runner.py lines 72–81) — copy for `cmd` check execution:
```python
def _file_diff(cwd: Path) -> str:
    completed = subprocess.run(
        ["git", "diff", "HEAD"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout if completed.returncode == 0 else ""
```

**New check executor** — implement as standalone function called from `run_suite` loop (D-02: run all, no short-circuit; D-03: 60s default timeout, override per-check):
```python
def _run_checks(checks: list, cwd: Path) -> tuple[bool, list[dict]]:
    """Run all checks; return (gate_pass, results_list). Never short-circuits."""
    results = []
    for check in checks:
        if check.type == "cmd":
            try:
                cp = subprocess.run(
                    check.run,
                    shell=True,
                    cwd=cwd,
                    capture_output=True,
                    text=True,
                    timeout=getattr(check, "timeout", 60),
                )
                passed = cp.returncode == 0
                detail = cp.stdout[:200] if passed else cp.stderr[:200]
            except subprocess.TimeoutExpired:
                passed = False
                detail = "timeout"
        elif check.type == "file_exists":
            passed = (cwd / check.path).exists()
            detail = ""
        elif check.type == "file_contains":
            p = cwd / check.path
            passed = p.exists() and check.text in p.read_text()
            detail = ""
        results.append({"type": check.type, "pass": passed, "detail": detail})
    gate_pass = all(r["pass"] for r in results)
    return gate_pass, results
```

**Existing `run_suite` task loop** (runner.py lines 311–381) — hook points:

1. **Run header** — print before `for task_id, spec in tasks:` loop (after tasks list built and providers resolved):
```python
click.echo(f"{len(tasks)} tasks · max {max_turns} turns/task", err=False)
```

2. **Turn cap** — `_drive_task` currently calls `run_turn` once with no cap. The cap hooks at the `run_turn` call level by wrapping the loop. The least-invasive approach: add `max_turns` parameter to `_drive_task` and pass it down; the drive loop counts iterations of `run_turn` (each `run_turn` call = one turn). For the capped-never-finishes case, use a counter around `run_turn` calls and break when `turn_count >= max_turns`.

3. **Capped row recording** (D-05) — matches existing `crash_reason` row path. In `run_suite` loop (runner.py lines 358–378), add alongside existing `crash_reason` guard:
```python
row = {
    ...
    "capped": capped,          # new field: bool
    "gate_pass": gate_pass,    # new field: bool (vacuously True if no checks)
    "checks": check_results,   # new field: list[dict]
    "success": False if (crash_reason or capped) else ...,
    "judge_verdict": "skipped" if (crash_reason or capped) else judge_verdict,
    ...
}
```

**Existing `_record_model` / `get_config`** (runner.py line 107):
```python
def _record_model(model: str | None) -> str:
    return model or get_config().default_model
```
The same `get_config()` call is the pattern for reading config defaults. The new `[eval]` config reader follows this exact style.

**`run_suite` signature** — add `max_turns: int | None = None` parameter; resolve inside function against config default (same precedence pattern as `judge_model`).

---

### `voss/eval/judge.py` — skip-on-capped path

**Analog:** `voss/eval/runner.py` lines 339–356 — existing `crash_reason is None` guard before judge call

**Existing guard** (runner.py lines 339–345):
```python
verdict = None
judge_verdict = "skipped"
judge_rationale = ""
if crash_reason is None and judge_provider is not None:
    try:
        verdict, judge_verdict = asyncio.run(
            judge_run(...)
        )
```

**New guard** — extend the condition to also skip when capped (D-05):
```python
if crash_reason is None and not capped and judge_provider is not None:
```
`judge.py` itself does not change. The skip is in `runner.py`.

---

### `voss/eval/summary.py` — gate-pass vs judge-rate columns

**Analog:** `voss/eval/summary.py` (self) — existing `passes` / `overall_rate` aggregation pattern

**Existing aggregation pattern** (summary.py lines 55–62):
```python
total = len(rows)
scored = [row for row in rows if row.get("success") is not None]
passes = sum(1 for row in scored if row["success"])
overall_rate = passes / len(scored) if scored else 0.0
```

**New aggregation** — add alongside (same `.get()` guard for back-compat with rows lacking the new fields):
```python
gate_rows = [row for row in rows if row.get("gate_pass") is not None]
gate_passes = sum(1 for row in gate_rows if row["gate_pass"])
gate_rate = gate_passes / len(gate_rows) if gate_rows else None

judge_rows = [row for row in rows if row.get("judge_verdict") not in (None, "skipped", "error")]
judge_passes = sum(1 for row in judge_rows if row.get("judge_verdict") == "pass")
judge_rate = judge_passes / len(judge_rows) if judge_rows else None
```

**Existing template call** (summary.py lines 81–97) — pass new keys into context dict alongside existing keys:
```python
rendered = render_package_template(
    "voss",
    "templates/eval/summary.md.jinja",
    {
        ...  # existing keys unchanged
        "gate_rate": f"{gate_rate:.0%}" if gate_rate is not None else "n/a",
        "gate_passes": gate_passes,
        "gate_total": len(gate_rows),
        "judge_rate": f"{judge_rate:.0%}" if judge_rate is not None else "n/a",
        "judge_passes": judge_passes,
        "judge_total": len(judge_rows),
    },
)
```

**Per-task dict** (summary.py lines 64–79) — add `gate_pass_rate` alongside existing `pass_rate`:
```python
tasks.append({
    "id": task_id,
    "runs": len(task_rows),
    "pass_rate": rate,          # existing: overall success rate
    "gate_pass_rate": ...,      # new: gate-only rate
    "mean_cost": cost_s,
})
```

---

### `voss/templates/eval/summary.md.jinja` — gate-pass and judge-rate columns

**Analog:** `voss/templates/eval/summary.md.jinja` (self)

**Existing template** (full file, 16 lines):
```jinja
# voss eval — {{ run_name }}

- runs: {{ total }}
- provider: `{{ provider }}` · model: `{{ model }}`
- overall success rate: {{ overall_rate }} ({{ passes }}/{{ scored_count }})
- mean cost: {{ mean_cost }}
- conf_corr_r: {{ conf_corr_r }} (n={{ corr_n }})

## Per-task

| task | runs | pass rate | mean cost |
|------|-----:|----------:|----------:|
{% for task in tasks -%}
| `{{ task.id }}` | {{ task.runs }} | {{ task.pass_rate }} | {{ task.mean_cost }} |
{% endfor %}
```

**New lines to add** in header section (after `overall_rate`):
```jinja
- gate pass rate: {{ gate_rate }} ({{ gate_passes }}/{{ gate_total }})
- judge pass rate: {{ judge_rate }} ({{ judge_passes }}/{{ judge_total }})
```

**Per-task table** — add `gate pass` column:
```jinja
| task | runs | gate pass | pass rate | mean cost |
|------|-----:|----------:|----------:|----------:|
{% for task in tasks -%}
| `{{ task.id }}` | {{ task.runs }} | {{ task.gate_pass_rate }} | {{ task.pass_rate }} | {{ task.mean_cost }} |
{% endfor %}
```

**Warning:** `test_summary_md.py::test_summary_renders_exact_markdown_bytes` hardcodes the full rendered string. That test must be updated to match the new column layout when the template changes.

---

### `voss/harness/cli.py` — `eval_cmd` dev gate + `--max-turns` flag

**Analog:** `voss/harness/cli.py` `eval_cmd` (lines 3491–3535, self) + `voss/cli.py` env-check pattern

**Existing `eval_cmd`** (harness/cli.py lines 3491–3535):
```python
@click.command("eval")
@click.option("--suite", default="golden", show_default=True, help="Evaluation suite name.")
@click.option("--stub", is_flag=True, help="Use deterministic stub provider.")
@click.option("--live", is_flag=True, help="Mark run as live provider evaluation.")
@click.option("-k", "k", default=1, show_default=True, type=int, help="Runs per task.")
@click.option("--out", "out_path", default=None, ...)
@click.option("--judge-model", default=None, help="Override judge model.")
@click.option("--task", default=None, help="Run a single task id.")
@click.option("--auth", "auth_pref", type=click.Choice(AUTH_CHOICES), default="auto", ...)
def eval_cmd(suite, stub, live, k, out_path, judge_model, task, auth_pref) -> None:
    """Run the golden evaluation suite."""
    from voss.eval.runner import run_suite
    run_suite(suite=suite, stub=stub, live=live, k=k, out=out_path,
              judge_model=judge_model, task=task, auth_pref=auth_pref)
```

**Dev gate pattern to copy from** — `voss/cli.py` `_should_use_native_tui` / `os.environ.get` (lines 236–238):
```python
def _should_use_native_tui() -> bool:
    return os.environ.get("VOSS_USE_TUI", "").lower() in ("1", "true", "yes")
```

**Existing no-creds exit pattern** (runner.py lines 246–248):
```python
click.echo(NO_CREDS_MESSAGE, err=True)
raise click.exceptions.Exit(code=2)
```

**Dev gate implementation** — check at top of `eval_cmd` callback (D-07), before any `run_suite` call:
```python
def eval_cmd(...) -> None:
    """Run the golden evaluation suite."""
    if os.environ.get("VOSS_DEV") != "1":
        click.echo("voss eval: internal tool — set VOSS_DEV=1 to run", err=True)
        raise click.exceptions.Exit(code=1)
    from voss.eval.runner import run_suite
    run_suite(...)
```

**New `--max-turns` option** — add alongside existing options with same style:
```python
@click.option("--max-turns", "max_turns", default=None, type=int,
              help="Turn cap per task (overrides config default).")
```
Pass `max_turns=max_turns` into `run_suite(...)`.

---

### `voss/harness/config.py` — new `[eval]` section reader

**Analog:** `voss/harness/config.py` `[agent]` section (lines 56–103, 209–225) — exact same pattern

**Existing `[agent]` section parser** (config.py lines 56–61):
```python
_AGENT_BLOCK = re.compile(r"^\[agent\][^\[]*", re.MULTILINE)

def _parse_agent_section(text: str) -> dict[str, str]:
    m = _AGENT_BLOCK.search(text)
    if not m:
        return {}
    block = m.group(0)
    return {k: v for k, v in _KV.findall(block)}
```

**Existing `load_agent_config`** (config.py lines 93–102):
```python
def load_agent_config() -> dict[str, str]:
    """Return the `[agent]` section as a dict. Missing file / section -> {}."""
    p = config_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text()
    except OSError:
        return {}
    return _parse_agent_section(text)
```

**Existing `get_max_iterations` accessor** (config.py lines 209–225) — copy exactly for `get_eval_max_turns`:
```python
def get_max_iterations() -> int:
    """Resolve agent.max_iterations, falling back to RuntimeConfig default."""
    default = RuntimeConfig().max_iterations
    cfg = load_agent_config()
    raw = cfg.get("max_iterations")
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        warnings.warn(
            f"[agent] max_iterations = {raw!r} is not an integer; "
            f"falling back to default {default}",
            RuntimeWarning,
            stacklevel=2,
        )
        return default
```

**New `[eval]` section** — add these three items following the same pattern:
```python
_EVAL_BLOCK = re.compile(r"^\[eval\][^\[]*", re.MULTILINE)

def _parse_eval_section(text: str) -> dict[str, str]:
    m = _EVAL_BLOCK.search(text)
    if not m:
        return {}
    return {k: v for k, v in _KV.findall(m.group(0))}

def load_eval_config() -> dict[str, str]:
    """Return the `[eval]` section as a dict. Missing file / section -> {}."""
    p = config_path()
    if not p.exists():
        return {}
    try:
        text = p.read_text()
    except OSError:
        return {}
    return _parse_eval_section(text)

DEFAULT_MAX_TURNS = 15
DEFAULT_JUDGE_MODEL = "gpt-4.1-mini"  # concrete id chosen by planner from codex auth

def get_eval_max_turns() -> int:
    """Resolve [eval] max_turns (default 15)."""
    cfg = load_eval_config()
    raw = cfg.get("max_turns")
    if raw is None:
        return DEFAULT_MAX_TURNS
    try:
        return int(raw)
    except (TypeError, ValueError):
        warnings.warn(
            f"[eval] max_turns = {raw!r} is not an integer; falling back to {DEFAULT_MAX_TURNS}",
            RuntimeWarning, stacklevel=2,
        )
        return DEFAULT_MAX_TURNS

def get_eval_judge_model() -> str:
    """Resolve [eval] judge_model (default smaller gpt-5.x variant)."""
    cfg = load_eval_config()
    return cfg.get("judge_model", DEFAULT_JUDGE_MODEL)
```

---

### `tests/eval/conftest.py` — autouse `VOSS_DEV=1` env

**Analog:** `tests/harness/conftest.py` lines 28–31 — autouse env fixture pattern

**Existing autouse pattern** (harness/conftest.py lines 28–31):
```python
@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path
```

**New `tests/eval/conftest.py`** — minimal, autouse sets `VOSS_DEV=1`:
```python
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _set_voss_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """All eval tests run with VOSS_DEV=1 so the gated verb is accessible."""
    monkeypatch.setenv("VOSS_DEV", "1")
```

**Note:** The subprocess-based tests in `test_voss_eval_stub.py` build their own env dict via `os.environ.copy()` — they must explicitly carry `VOSS_DEV=1` forward (or the conftest fixture won't affect subprocess env). The planner should note that `_run_eval` in `test_voss_eval_stub.py` needs `env["VOSS_DEV"] = "1"` added to its env dict (the gate-test for missing var clears it explicitly).

---

### `tests/eval/golden/*/task.toml` — `[[checks]]` retrofit

**Analog:** `tests/eval/golden/01-analyze/task.toml` (self) — TOML array-of-tables syntax

**Existing task.toml structure** (01-analyze/task.toml lines 1–14):
```toml
prompt = "Analyze this repository and write architecture.md describing what it does."
mode = "edit"
rubric = """..."""
judge_inputs = ["final", "file_diff"]
auto_approve_edits = true
```

**TOML `[[checks]]` array-of-tables form** (D-01 — each `[[checks]]` appends one check):
```toml
[[checks]]
type = "file_exists"
path = ".voss/architecture.md"

[[checks]]
type = "cmd"
run = "test -s .voss/architecture.md"
```

**Per-task check contracts** (from SPEC §3 and M5-05-SUMMARY golden contracts):
- `01-analyze`: `file_exists` `.voss/architecture.md`
- `02-plan-only`: `cmd` `git diff --quiet HEAD` (no file modifications)
- `03-approved-edit`: `file_contains` `calc.py` `sum_two` + `file_contains` `calc.py` absent `add(` → use two `file_contains` checks; also `file_contains` `main.py` `sum_two`
- `04-validation`: `cmd` `python -m voss.cli check sample.voss` exits 0
- `05-resume`: `file_exists` or `cmd` checking session record has two turns (judge-only fallback acceptable — planner decides)
- `06-fetch-summarize`: `file_exists` `summary.txt` + `file_contains` `summary.txt` `Example`

---

## Shared Patterns

### Dev-gate env check
**Source:** `voss/cli.py` lines 236–238 (env var check) + `voss/eval/runner.py` lines 246–248 (Exit pattern)
**Apply to:** `eval_cmd` in `voss/harness/cli.py`
```python
if os.environ.get("VOSS_DEV") != "1":
    click.echo("voss eval: internal tool — set VOSS_DEV=1 to run", err=True)
    raise click.exceptions.Exit(code=1)
```

### Config section reader (regex parse)
**Source:** `voss/harness/config.py` lines 25–103 (`[harness]`/`[agent]` sections)
**Apply to:** new `[eval]` section in `voss/harness/config.py`
- Pattern: `re.compile(r"^\[section\][^\[]*", re.MULTILINE)` + `_KV.findall(block)`
- Accessor: `load_<section>_config()` returns `dict[str, str]`, missing → `{}`
- Typed getter: `get_<key>() -> T` with `warnings.warn` on bad value, fallback to default

### subprocess check (60s timeout, cwd-relative)
**Source:** `voss/eval/runner.py` lines 72–81 (`_file_diff`) + lines 52–68 (`_prepare_fixture`)
**Apply to:** `_run_checks` cmd check executor in `voss/eval/runner.py`
```python
subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True,
               timeout=60, check=False)
```

### Pydantic discriminated union with `extra="forbid"`
**Source:** `voss/eval/suite.py` lines 11–14 (`TaskSpec` ConfigDict) + `voss/eval/judge.py` lines 12–19 (`Verdict`)
**Apply to:** `AnyCheck` union + per-check models in `voss/eval/suite.py`
- All check sub-models use `ConfigDict(extra="forbid")`
- `type` field is `Literal["cmd"]` etc. (the discriminator key)

### JSONL row extension (never break existing fields)
**Source:** `voss/eval/runner.py` lines 358–378 (`row` dict)
**Apply to:** new `gate_pass`, `capped`, `checks` fields in runner row
- New fields append at end of existing dict literal
- Existing tests pin `REQUIRED_FIELDS` set — planner must update that set in `test_voss_eval_stub.py`

### `judge_verdict: "skipped"` reuse
**Source:** `voss/eval/runner.py` line 340 + `tests/eval/test_voss_eval_stub.py` line 91
**Apply to:** capped task path (D-05)
- Capped ⇒ `judge_verdict = "skipped"`, `success = False`, `capped = True`
- Existing test already asserts `judge_verdict == "skipped"` for stub mode — capped path reuses same sentinel

### Same-model warning (stderr, never error)
**Source:** `voss/eval/runner.py` lines 246–248 (`click.echo(..., err=True)`) + D-11
**Apply to:** judge model equality check in `run_suite`
```python
if judge_model_eff == model_eff:
    click.echo(
        f"voss eval: judge model == actor model ({judge_model_eff!r}); proceeding",
        err=True,
    )
```

---

## No Analog Found

All files have close analogs in the codebase. No entries.

---

## Metadata

**Analog search scope:** `voss/eval/`, `voss/harness/config.py`, `voss/harness/cli.py`, `voss/cli.py`, `tests/eval/`, `tests/harness/conftest.py`
**Files scanned:** 14
**Pattern extraction date:** 2026-06-10
