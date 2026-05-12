# Phase M5: Eval and Distribution Prep - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 27 (22 NEW + 5 MODIFIED, ordered by Wave 0..5)
**Analogs found:** 27 / 27

Every M5 file has a direct in-tree analog. M5 is overwhelmingly orchestration: a new `voss/eval/` package wires existing primitives (`Plan.confidence` at agent.py:46, `RunRecord.cost_usd` at session.py:77, `LiteLLMProvider.complete` JSON-mode at litellm_provider.py:32-50, `PermissionGate(auto_yes=True)` at permissions.py:98-104) plus three stdlib pieces (`tomllib`, `statistics.correlation`, `venv`). The CLI surface follows the M2/M4 `AGENT_COMMANDS` registration shape (voss/harness/cli.py:795-810). The wheel smoke extends the existing tests/packaging/test_entrypoint.py:65 venv pattern. Mirrors M4-PATTERNS.md structure.

---

## File Classification

### Wave 0 — suite loader + fixture isolation (gate: blocks all eval orchestration)

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `voss/eval/__init__.py` | NEW | package marker | static | `voss_runtime/memory/__init__.py:1-3` (empty re-export package) | exact |
| `voss/eval/suite.py` | NEW | suite loader + TaskSpec pydantic | file-I/O + transform | `voss/harness/agent.py:43-58` (`Plan` pydantic) + `voss/harness/config.py:_parse_harness_section` (tomllib usage) | role-match |
| `tests/eval/__init__.py` | NEW | package marker | static | `tests/harness/__init__.py` (empty file) | exact |
| `tests/eval/test_suite_loads.py` | NEW | test (suite discovery) | request-response (filesystem) | `tests/parser/test_examples.py:1-30` (directory walk + count assert) | role-match |
| `tests/eval/test_task_spec.py` | NEW | test (pydantic validation) | transform | `tests/harness/test_agent_integration.py` (pydantic round-trip pattern) | role-match |
| `tests/eval/test_fixture_isolation.py` | NEW | test (tempdir + git init) | file-I/O | `tests/examples/helpers.py:60-69` (`run_voss` subprocess) + `tests/harness/test_session.py` (tmp_path fixture) | role-match |

### Wave 1 — judge call + auth role extension

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `voss/eval/judge.py` | NEW | scorer + Verdict pydantic + provider call | request-response (LLM) | `voss/harness/agent.py:43-58` (`Plan` BaseModel) + litellm_provider.py:32-50 (response_format machinery) | exact |
| `voss/harness/auth.py:resolve` | MODIFY (+1 LOC) | auth resolver | static | self (existing `def resolve(preference: str = "auto")` at line 332) | exact (in-file) |
| `tests/eval/test_judge_verdict.py` | NEW | test (judge JSON-mode) | request-response | `tests/harness/test_agent_integration.py:21-50` (FakeProvider pattern) | exact |
| `tests/eval/test_judge_skipped.py` | NEW | test (crash path) | request-response | `tests/harness/test_agent_integration.py` (raise-from-FakeProvider variant) | role-match |
| `tests/harness/test_auth.py` | MODIFY | test (role kwarg cases) | request-response | self (existing `test_auth.py` Resolution cases) | exact (in-file) |

### Wave 2 — CLI subcommand + runner + JSONL

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `voss/eval/runner.py` | NEW | orchestrator (suite × k loops) | event-driven (asyncio) | `voss/harness/cli.py:do_cmd` (asyncio.run + run_turn dispatch) + `voss/harness/recorder.py:80-119` (`absorb(plan)` → RunRecord round-trip) | role-match |
| `voss/harness/cli.py:AGENT_COMMANDS` | MODIFY (+1 entry) | CLI registration | static | self (existing tuple at lines 795-804) | exact (in-file) |
| `tests/eval/test_cli_options.py` | NEW | test (Click options surface) | request-response (CliRunner) | `tests/cli/test_run.py:22-58` (CliRunner + monkeypatch) | exact |
| `tests/eval/test_voss_eval_stub.py` | NEW | test (stub smoke + JSONL shape) | request-response (subprocess) | `tests/examples/helpers.py:60-69` (`run_voss`) + `tests/harness/test_session_redaction.py` (JSON shape assertions) | role-match |
| `tests/eval/test_live_signals.py` | NEW | test (`@pytest.mark.live`) | request-response | existing `@pytest.mark.live` tests under tests/harness/ | role-match |

### Wave 3 — summary + Pearson + gitignore guard

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `voss/eval/summary.py` | NEW | Markdown generator + Pearson | transform | `voss/harness/recorder.py` (dict aggregation) + stdlib `statistics.correlation` (Pattern 5 below) | role-match |
| `tests/eval/test_pearson.py` | NEW | test (Pearson reference) | transform | unit-test pattern; no direct analog in tree (stdlib call) | none (greenfield, 5-LOC) |
| `tests/eval/test_summary_md.py` | NEW | test (Markdown shape) | transform | `tests/harness/test_recorder.py` (string-assertion pattern) | role-match |
| `tests/eval/test_gitignore.py` | NEW | test (.voss/.gitignore content) | file-I/O | `voss/harness/cognition.py:575-582` (`write_voss_gitignore` source) | role-match |

### Wave 4 — five golden task fixtures

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `tests/eval/golden/01-analyze/{task.toml,fixture/}` | NEW | fixture (TOML + seed repo) | static | `voss/harness/cognition.py:bootstrap_prompt` (analyze prompt surface) | role-match |
| `tests/eval/golden/02-plan-only/{task.toml,fixture/}` | NEW | fixture (plan-mode task) | static | M1 D-07 plan-mode contract; permissions.py:108-109 (READ_ONLY denial) | role-match |
| `tests/eval/golden/03-approved-edit/{task.toml,fixture/}` | NEW | fixture (edit + auto_approve) | static | `voss/harness/permissions.py:98-104` (auto_yes path) | exact |
| `tests/eval/golden/04-validation/{task.toml,fixture/}` | NEW | fixture (.voss sample for `voss check`) | static | `samples/classify.voss` (minimal sample) | exact |
| `tests/eval/golden/05-resume/{task.toml,fixture/}` | NEW | fixture (spawn-cancel-resume) | event-driven (asyncio.Task.cancel) | `voss/harness/session.py:133-192` (save/load round-trip) | role-match |

### Wave 5 — packaging smoke + README polish

| File | New/Mod | Role | Data Flow | Closest Analog | Match Quality |
|------|---------|------|-----------|----------------|---------------|
| `tests/packaging/test_wheel_install.py` | NEW | test (wheel-in-tempvenv, `@pytest.mark.slow`) | request-response (subprocess) | `tests/packaging/test_entrypoint.py:65-105` (`test_editable_install_exposes_voss_help`) | exact |
| `tests/packaging/test_readme.py` | NEW | test (README content asserts) | file-I/O | `tests/cli/test_check.py:70-97` (string-content assert pattern) | role-match |
| `README.md` | MODIFY | docs (install section polish per D-18) | static | self (existing install block) | exact (in-file) |

---

## Pattern Assignments

### `voss/eval/__init__.py` (NEW) — Wave 0 Pattern 0

**Analog:** `voss_runtime/memory/__init__.py:1-3` — empty package marker with optional re-exports.

**Target shape:**
```python
"""voss.eval — golden-suite evaluation harness (M5).

Public API:
    run_suite(suite, stub, k, out_dir, judge_model, task_id, auth_pref) -> Path
"""
from .runner import run_suite  # noqa: F401
```

**Adaptation notes:**
- Keep minimal; only re-export `run_suite` so `voss/harness/cli.py:eval_cmd` can `from voss.eval import run_suite`.
- The runner imports `suite`, `judge`, `summary` lazily — keeps Click startup fast.

---

### `voss/eval/suite.py` (NEW) — Wave 0 Pattern 1

**Analog:** `voss/harness/agent.py:43-58` (`Plan` BaseModel — pydantic field constraints, `Field(...)` description pattern) + RESEARCH §"Code Examples" task.toml load+validate snippet.

**Reference shape — `Plan` model** (agent.py:43-58):
```python
class Plan(BaseModel):
    rationale: str = Field(description="One-paragraph reasoning for the chosen approach.")
    steps: list[ToolCall] = Field(default_factory=list, description="Sequential tool calls.")
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Self-rated confidence the plan resolves the user's task. 0.0-1.0.",
    )
    open_question: str | None = Field(default=None, ...)
    final_when_done: str = Field(default="", ...)
```

**Target shape** (per RESEARCH lines 263-275 + CONTEXT D-07):
```python
"""Task suite loader + TaskSpec schema (M5 D-05, D-07)."""
from __future__ import annotations
import tomllib
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class TaskSpec(BaseModel):
    """Validated `task.toml` row. Mirrors M1 D-07 mode tiers + D-08 rubric shape."""
    model_config = ConfigDict(extra="forbid")  # reject unknown keys (RESEARCH §Common Pitfalls)

    prompt: str = Field(description="Prompt passed to `voss do`.")
    mode: Literal["plan", "edit", "auto"]
    rubric: str = Field(description="Plain-text PASS/FAIL criteria (D-08).")
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    provider: str | None = None
    model: str | None = None
    auto_approve_edits: bool = False


def load_task(task_dir: Path) -> TaskSpec:
    data = tomllib.loads((task_dir / "task.toml").read_text())
    return TaskSpec.model_validate(data)


def load_suite(suite_root: Path, suite: str = "golden") -> list[tuple[str, TaskSpec]]:
    """Return [(task_id, spec), ...] sorted by task_id. task_id = directory basename."""
    suite_dir = suite_root / suite if suite_root.name != suite else suite_root
    tasks: list[tuple[str, TaskSpec]] = []
    for task_dir in sorted(suite_dir.iterdir()):
        if not task_dir.is_dir() or not (task_dir / "task.toml").exists():
            continue
        tasks.append((task_dir.name, load_task(task_dir)))
    return tasks
```

**Adaptation notes:**
- `model_config = ConfigDict(extra="forbid")` rejects typos in `task.toml` (RESEARCH §Common Pitfalls: "schema drift").
- `task_id = directory basename` (D-05) — stable across runs; written to JSONL `task_id` field (D-04).
- Use `tomllib` (stdlib at 3.11+), NOT `tomli` (RESEARCH §"Don't Hand-Roll").
- No file I/O outside the suite dir; pure read.

---

### `voss/eval/judge.py` (NEW) — Wave 1 Pattern 2

**Analog:** `voss/harness/agent.py:43-58` (`Plan` shape) + `voss_runtime/providers/litellm_provider.py:32-50` (canonical `response_format=Pydantic` JSON-mode contract).

**Reference excerpt — LiteLLMProvider response_format machinery** (litellm_provider.py:32-50):
```python
if response_format is not None:
    kwargs["response_format"] = response_format

try:
    resp = await litellm.acompletion(**kwargs)
except Exception as e:
    raise ProviderError(f"{model}: {e}") from e

choice = resp.choices[0].message
text = choice.content or ""
usage = resp.usage
cost = float(getattr(resp, "_hidden_params", {}).get("response_cost", 0.0) or 0.0)

parsed = None
if response_format is not None and text:
    try:
        parsed = response_format.model_validate_json(text)
    except Exception as e:
        raise ParseError(f"Failed to parse {response_format.__name__}: {e}") from e
```

**Target shape** (per RESEARCH lines 140-155 + CONTEXT D-09):
```python
"""LLM-as-judge scorer (M5 D-08, D-09)."""
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict
from voss_runtime.providers.base import ModelProvider
from voss_runtime.providers.litellm_provider import ParseError


class Verdict(BaseModel):
    """Judge response, pydantic-validated via response_format=Verdict."""
    model_config = ConfigDict(extra="ignore")  # lenient (mirrors RunSemantics at agent.py:68)

    verdict: Literal["pass", "fail"]
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


JUDGE_SYSTEM = """You are an evaluator. Given a task prompt, the agent's final
answer, an optional file diff, and a rubric, decide if the run passed or failed.
Return ONLY a JSON object: {"verdict": "pass"|"fail", "confidence": 0.0-1.0,
"rationale": "<one paragraph>"}.
"""


async def judge_run(
    *,
    provider: ModelProvider,
    model: str,
    task_prompt: str,
    final: str,
    file_diff: str,
    rubric: str,
) -> tuple[Verdict | None, str]:
    """Return (Verdict, judge_verdict_str). On ParseError, returns (None, "skipped")."""
    user_msg = (
        f"## Task prompt\n{task_prompt}\n\n"
        f"## Agent final\n{final}\n\n"
        f"## File diff\n{file_diff}\n\n"
        f"## Rubric\n{rubric}\n"
    )
    try:
        resp = await provider.complete(
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=model,
            response_format=Verdict,
            temperature=0.0,
        )
    except ParseError:
        return None, "skipped"
    if resp.parsed is None:
        return None, "skipped"
    return resp.parsed, resp.parsed.verdict
```

**Adaptation notes:**
- `response_format=Verdict` reuses litellm_provider.py:32-50 verbatim — no provider extension needed.
- `ParseError` catch matches RESEARCH §"Pattern 2" fallback ("retry shape" optional in M5; recommended: single attempt + skipped).
- `temperature=0.0` for reproducibility (judge should not vary on identical inputs).
- `model_config = ConfigDict(extra="ignore")` matches `RunSemantics` lenient stance (agent.py:68); judge model may add fields.
- File diff produced by caller via `difflib.unified_diff` (RESEARCH §Standard Stack: stdlib).

---

### `voss/harness/auth.py:resolve` (MODIFY +1 LOC) — Wave 1

**Analog:** Self. Existing signature at line 332.

**Current shape** (auth.py:332):
```python
def resolve(preference: str = "auto") -> Resolution:
    """Decide which auth path to use.

    preference: auto | claude | codex | api | none
    """
    if preference == "none":
        return Resolution(source="none", detail="forced none")
    ...
```

**Target shape** (per RESEARCH §"Compiler/Runtime Gaps Flagged as Sub-Plans" line 476-477 + CONTEXT D-10):
```python
def resolve(preference: str = "auto", role: str | None = None) -> Resolution:
    """Decide which auth path to use.

    preference: auto | claude | codex | api | none
    role: optional logical role (e.g. "judge"); M5 pass-through, future versions
          may resolve a separate creds bucket per role. Today: role is ignored
          and the same Resolution applies to all roles.
    """
    if preference == "none":
        return Resolution(source="none", detail="forced none")
    ...
```

**Adaptation notes:**
- Single-line signature change. Body unchanged.
- `role` is intentionally ignored in v0.1 (RESEARCH §Assumptions A1: "trivial pass-through; if future contract differs, plan grows by one task").
- Pin in `tests/harness/test_auth.py`: a new test confirms `resolve(role="judge")` returns same Resolution as `resolve()` (regression guard if future change forgets pass-through).
- No callers of `resolve` need updating — `role` is a default-None keyword.

---

### `tests/harness/test_auth.py` (MODIFY) — Wave 1

**Analog:** Self. Existing `Resolution` assertion pattern.

**Target additions:**
```python
def test_resolve_accepts_role_kwarg(monkeypatch):
    """M5 D-10: role kwarg accepted, ignored in v0.1 (same Resolution as no role)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    from voss.harness.auth import resolve
    r_default = resolve()
    r_judge = resolve(role="judge")
    assert r_default.source == r_judge.source
    assert r_default.detail == r_judge.detail


def test_resolve_role_with_none_preference(monkeypatch):
    """role is ignored when preference='none'."""
    from voss.harness.auth import resolve
    r = resolve(preference="none", role="judge")
    assert r.source == "none"
```

**Adaptation notes:**
- Two tests minimum; pinned by M5-VALIDATION row `auth-resolve-role`.
- `-k role` keyword-matches these.

---

### `voss/eval/runner.py` (NEW, ~200 LOC) — Wave 2 Pattern 3

**Analog:** `voss/harness/cli.py:do_cmd` (existing `asyncio.run(run_turn(...))` dispatch pattern) + `voss/harness/recorder.py:80-119` (`absorb(plan)` → RunRecord round-trip).

**Reference excerpt — RunRecord shape** (session.py:60-77):
```python
@dataclass
class RunRecord:
    id: str
    started_at: str
    ended_at: str
    goal: str = ""
    plan: Optional[dict] = None
    ...
    cost_usd: float = 0.0
```

**Reference excerpt — PermissionGate auto-approve** (permissions.py:94-104):
```python
@dataclass
class PermissionGate:
    mode: Mode = "edit"
    store: PermissionStore | None = None
    auto_yes: bool = False  # for tests + non-interactive runs
    ...
    def needs_prompt(self, tool_name: str) -> bool:
        if self.auto_yes:
            return False
```

**Target shape (skeleton — full module per RESEARCH §"Architecture Patterns"):**
```python
"""Eval runner: suite × k loops, JSONL writer, signal extraction (M5 D-04, D-13, D-14)."""
from __future__ import annotations
import asyncio
import difflib
import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import click

from voss import __version__ as VOSS_VERSION
from voss.harness import auth as auth_mod
from voss.harness.agent import run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.session import SessionRecord, save, load
from voss.harness.tools import make_toolset
from voss.harness.render import PlainRenderer
from voss_runtime.providers import StubProvider, get as get_provider

from .suite import TaskSpec, load_suite
from .judge import judge_run, Verdict


SUITE_ROOT = Path("tests/eval")  # repo-relative; resolved against project_root


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _prepare_fixture(task_dir: Path, tmp: Path) -> Path:
    """Per-run hermetic git init (D-06). RESEARCH §Code Examples."""
    cwd = tmp / "fixture"
    shutil.copytree(task_dir / "fixture", cwd)
    git_env = {"GIT_AUTHOR_NAME": "eval", "GIT_AUTHOR_EMAIL": "eval@voss",
               "GIT_COMMITTER_NAME": "eval", "GIT_COMMITTER_EMAIL": "eval@voss"}
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=cwd, check=True)
    subprocess.run(["git", "add", "-A"], cwd=cwd, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=cwd, check=True, env={**os.environ, **git_env})
    return cwd


def _file_diff(cwd: Path) -> str:
    """Git diff vs initial commit (for judge file_diff input)."""
    result = subprocess.run(["git", "diff", "HEAD"], cwd=cwd, capture_output=True, text=True)
    return result.stdout


def _extract_signals(record: SessionRecord) -> tuple[float | None, float | None]:
    """RESEARCH §Code Examples: cost from RunRecord.cost_usd; confidence from first RunRecord.plan."""
    if not record.runs:
        return None, None
    total_cost = sum(float(r.get("cost_usd") or 0.0) for r in record.runs) or None
    first_plan = record.runs[0].get("plan") or {}
    conf = first_plan.get("confidence")
    return total_cost, (float(conf) if conf is not None else None)


def _append_row(path: Path, row: dict) -> None:
    """JSONL append. RESEARCH §Code Examples."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")


async def _drive_task(task_id: str, spec: TaskSpec, cwd: Path, *, provider, model: str,
                       permissions: PermissionGate) -> tuple[SessionRecord, str, bool]:
    """Run one task once. Returns (session, final, crashed)."""
    record = SessionRecord.new(cwd=cwd, model=model)
    try:
        if task_id.startswith("05-resume"):
            return await _drive_resume(record, spec, cwd, provider, model, permissions)
        result = await run_turn(
            spec.prompt,
            tools=make_toolset(cwd),
            cwd=cwd,
            renderer=PlainRenderer(),
            provider=provider,
            permissions=permissions,
            model=model,
        )
        return record, result.final, False
    except Exception:
        return record, "", True


async def _drive_resume(record, spec, cwd, provider, model, permissions):
    """Task 05: spawn → cancel mid-turn → resume. RESEARCH §Pattern 4."""
    task = asyncio.create_task(run_turn(
        spec.prompt, tools=make_toolset(cwd), cwd=cwd,
        renderer=PlainRenderer(), provider=provider, permissions=permissions,
        model=model, session_id=record.id,
    ))
    await asyncio.sleep(0.05)  # let first tool dispatch begin
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    # Resume: load + replay
    record2, history2 = load(record.id, cwd=cwd)
    result = await run_turn(
        spec.prompt, history=history2, tools=make_toolset(cwd), cwd=cwd,
        renderer=PlainRenderer(), provider=provider, permissions=permissions,
        model=model, session_id=record2.id,
    )
    return record2, result.final, False


def run_suite(*, suite: str = "golden", stub: bool = False, k: int = 3,
              out_dir: Path | None = None, judge_model: str | None = None,
              task_id: str | None = None, auth_pref: str = "auto") -> Path:
    """Top-level entry: load suite, run × k, write JSONL + summary. Returns out_dir."""
    project_root = Path.cwd()
    suite_root = project_root / SUITE_ROOT / "golden"

    # Provider resolution (D-10, D-11)
    if stub:
        provider = StubProvider()
        model = "__stub__"
    else:
        res = auth_mod.resolve(preference=auth_pref)
        if res.source == "none":
            click.echo(
                "voss eval: no provider creds — pass --stub for hermetic smoke or run /login",
                err=True,
            )
            raise click.exceptions.Exit(code=2)
        provider = get_provider()  # uses default_model selection
        model = "__default__"

    # Judge provider (D-10 with role="judge")
    judge_res = auth_mod.resolve(preference=auth_pref, role="judge")
    judge_provider = StubProvider() if (stub and judge_res.source == "none") else get_provider()
    judge_model_eff = judge_model or model

    # Output directory (D-02, D-03)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = out_dir or (project_root / ".voss" / "eval" / ts)
    out.mkdir(parents=True, exist_ok=True)
    jsonl_path = out / "runs.jsonl"

    # Suite load (D-05)
    all_tasks = load_suite(suite_root, suite=suite)
    tasks = [(tid, spec) for tid, spec in all_tasks if task_id is None or tid == task_id]
    if not tasks:
        raise click.ClickException(f"no tasks found in suite={suite!r} matching task={task_id!r}")

    for tid, spec in tasks:
        for run_idx in range(k):
            with tempfile.TemporaryDirectory(prefix=f"voss-eval-{tid}-") as tmp_str:
                tmp = Path(tmp_str)
                cwd = _prepare_fixture(suite_root / tid, tmp)
                gate = PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)
                started_at = _now_iso()
                t0 = time.perf_counter()
                record, final, crashed = asyncio.run(_drive_task(
                    tid, spec, cwd, provider=provider, model=model, permissions=gate))
                duration_s = time.perf_counter() - t0
                cost, confidence = _extract_signals(record)
                if stub:
                    cost = None  # D-11: stub cost is null, NOT a token-count estimate
                diff = _file_diff(cwd)

                # Judge or skip (D-08, D-11)
                if crashed:
                    verdict_str, judge_conf, rationale = "skipped", 0.0, "agent crashed"
                    success = False
                elif stub and judge_res.source == "none":
                    verdict_str, judge_conf, rationale = "skipped", 0.0, "no judge creds under stub"
                    success = None
                else:
                    verdict, verdict_str = asyncio.run(judge_run(
                        provider=judge_provider, model=judge_model_eff,
                        task_prompt=spec.prompt, final=final, file_diff=diff, rubric=spec.rubric,
                    ))
                    judge_conf = verdict.confidence if verdict else 0.0
                    rationale = verdict.rationale if verdict else "(unparseable)"
                    success = (verdict_str == "pass") if verdict_str != "skipped" else None

                row = {
                    "task_id": tid,
                    "run_idx": run_idx,
                    "success": success,
                    "cost_usd": cost,
                    "confidence": confidence,
                    "duration_s": round(duration_s, 3),
                    "judge_verdict": verdict_str,
                    "judge_confidence": judge_conf,
                    "judge_rationale": rationale,
                    "provider": provider.__class__.__name__,
                    "model": model,
                    "judge_model": judge_model_eff,
                    "seed": None,
                    "voss_version": VOSS_VERSION,
                    "started_at": started_at,
                }
                _append_row(jsonl_path, row)

    # Markdown summary (handled by summary.py, Wave 3)
    from .summary import write_summary
    write_summary(jsonl_path, out / "summary.md")
    return out
```

**Adaptation notes:**
- All cost/confidence extraction reads exact fields from `session.py:60-77` (`RunRecord.cost_usd`) and `agent.py:46` (`Plan.confidence`). No new model fields.
- `PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)` — Option A from RESEARCH §Pattern 3 (no permissions.py change).
- `_drive_resume` follows RESEARCH §Pattern 4 (`asyncio.Task.cancel()`); guarded by RESEARCH §Assumption A2 (CancelledError propagates past per-step `except Exception`).
- Stub-cost = `None` enforced AFTER signal extraction (CONTEXT D-11 explicit rejection of token-count fakes; M5-VALIDATION row `jsonl-cost-stub-null`).
- Loud-failure no-creds path uses exact string from CONTEXT D-10: `"voss eval: no provider creds — pass --stub for hermetic smoke or run /login"`.
- Output path `.voss/eval/<timestamp>/` is durable (D-03; M2 .gitignore at cognition.py:581 only ignores `sessions/`).
- JSONL row schema is the D-04 allowlist; sort_keys for diff stability.
- All run dispatch is sequential (D-12 explicit — keeps cost predictable).

---

### `voss/harness/cli.py:AGENT_COMMANDS` (MODIFY) — Wave 2 Pattern 4

**Analog:** Self. Existing tuple at lines 795-810.

**Reference excerpt** (cli.py:795-810):
```python
AGENT_COMMANDS = (
    do_cmd,
    chat_cmd,
    edit_cmd,
    doctor_cmd,
    sessions_cmd,
    resume_cmd,
    tools_cmd,
    config_cmd,
)


def register(group: click.Group) -> None:
    """Attach all agent commands to a click Group."""
    for cmd in AGENT_COMMANDS:
        group.add_command(cmd)
```

**Target additions** (per RESEARCH §"Pattern 1: Click subcommand registration"):

1. Define `eval_cmd` in `voss/harness/cli.py` (alongside `do_cmd`, before the `AGENT_COMMANDS` tuple):
```python
@click.command("eval")
@click.option("--suite", default="golden", help="Suite name under tests/eval/.")
@click.option("--stub", is_flag=True, help="Force StubProvider (CI smoke).")
@click.option("--live", is_flag=True, help="No-op convenience flag; live is the default.")
@click.option("-k", "k", type=int, default=3, help="Runs per task.")
@click.option("--out", "out_dir", type=click.Path(path_type=Path), default=None,
              help="Override .voss/eval/<timestamp>/ output dir.")
@click.option("--judge-model", "judge_model", default=None,
              help="Override resolved judge model (default: same as agent).")
@click.option("--task", "task_id", default=None,
              help="Run a single task by id (e.g. 02-plan-only).")
@click.option("--auth", "auth_pref", type=click.Choice(AUTH_CHOICES), default="auto",
              help="Auth resolution preference.")
def eval_cmd(suite, stub, live, k, out_dir, judge_model, task_id, auth_pref):
    """Run the golden eval suite and write JSONL + Markdown report."""
    from voss.eval import run_suite
    out = run_suite(
        suite=suite, stub=stub, k=k, out_dir=out_dir,
        judge_model=judge_model, task_id=task_id, auth_pref=auth_pref,
    )
    click.echo(f"eval complete: {out}")
```

2. Append `eval_cmd` to `AGENT_COMMANDS` tuple at line 795-804:
```python
AGENT_COMMANDS = (
    do_cmd,
    chat_cmd,
    edit_cmd,
    doctor_cmd,
    sessions_cmd,
    resume_cmd,
    tools_cmd,
    config_cmd,
    eval_cmd,  # NEW (M5 D-01)
)
```

**Adaptation notes:**
- `AUTH_CHOICES` already exists in `voss/harness/cli.py` (used by `do_cmd` and `chat_cmd`); reuse verbatim.
- Lazy `from voss.eval import run_suite` keeps Click startup fast (eval imports asyncio + tomllib only when invoked).
- `--live` is intentionally a no-op (live is default per D-10) — declared for future-proofing per CONTEXT D-01.
- `register(main)` at line 807-810 picks it up automatically via the tuple; no `voss/cli.py` change needed.
- M5-VALIDATION row `cli-eval-command` greps Click param names — preserve `--suite`, `--stub`, `--live`, `-k`, `--out`, `--judge-model`, `--task` exactly.

---

### `voss/eval/summary.py` (NEW, ~80 LOC) — Wave 3 Pattern 5

**Analog:** RESEARCH §Pattern 5 (stdlib `statistics.correlation`) + recorder.py-style aggregation. No direct in-tree analog for Markdown generation; greenfield prose template.

**Reference excerpt — Pearson r via stdlib** (RESEARCH §Pattern 5):
```python
from statistics import correlation
r = correlation(
    [row["confidence"] for row in rows if row["confidence"] is not None],
    [1.0 if row["success"] else 0.0 for row in rows if row["confidence"] is not None],
)
```

**Target shape:**
```python
"""Markdown summary generator + Pearson r aggregator (M5 D-15, EVAL-04)."""
from __future__ import annotations
import json
import statistics
from collections import defaultdict
from pathlib import Path


def _read_rows(jsonl_path: Path) -> list[dict]:
    return [json.loads(line) for line in jsonl_path.read_text().splitlines() if line.strip()]


def _pearson(rows: list[dict]) -> tuple[float | None, int]:
    """Return (r, n). n is count of rows where both confidence + success are non-null."""
    pairs = [
        (r["confidence"], 1.0 if r["success"] else 0.0)
        for r in rows
        if r["confidence"] is not None and r["success"] is not None
    ]
    if len(pairs) < 2:
        return None, len(pairs)
    confs, succs = zip(*pairs)
    # statistics.correlation raises if all values equal — guard.
    if len(set(confs)) < 2 or len(set(succs)) < 2:
        return None, len(pairs)
    return statistics.correlation(confs, succs), len(pairs)


def write_summary(jsonl_path: Path, summary_path: Path) -> Path:
    rows = _read_rows(jsonl_path)
    by_task: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_task[r["task_id"]].append(r)

    total = len(rows)
    scored = [r for r in rows if r["success"] is not None]
    passes = sum(1 for r in scored if r["success"])
    overall_rate = (passes / len(scored)) if scored else 0.0
    costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
    mean_cost = (sum(costs) / len(costs)) if costs else None
    r, n = _pearson(rows)

    provider = rows[0]["provider"] if rows else "n/a"
    model = rows[0]["model"] if rows else "n/a"

    lines = [
        f"# voss eval — {jsonl_path.parent.name}",
        "",
        f"- runs: {total}",
        f"- provider: `{provider}` · model: `{model}`",
        f"- overall success rate: {overall_rate:.0%} ({passes}/{len(scored)})",
        f"- mean cost: {('$%.4f' % mean_cost) if mean_cost is not None else 'n/a'}",
        f"- conf_corr_r: {('%.3f' % r) if r is not None else 'n/a'} (n={n})",
        "",
        "## Per-task",
        "",
        "| task | runs | pass rate | mean cost |",
        "|------|-----:|----------:|----------:|",
    ]
    for tid in sorted(by_task):
        trs = by_task[tid]
        ts = [r for r in trs if r["success"] is not None]
        tp = sum(1 for r in ts if r["success"])
        tcosts = [r["cost_usd"] for r in trs if r["cost_usd"] is not None]
        tmc = (sum(tcosts) / len(tcosts)) if tcosts else None
        rate = f"{tp / len(ts):.0%}" if ts else "n/a"
        cost_s = f"${tmc:.4f}" if tmc is not None else "n/a"
        lines.append(f"| `{tid}` | {len(trs)} | {rate} | {cost_s} |")

    summary_path.write_text("\n".join(lines) + "\n")
    return summary_path
```

**Adaptation notes:**
- `statistics.correlation` raises `StatisticsError` when all values are identical; guard with `len(set(...)) < 2` (RESEARCH §Assumption A6: stub may return constant confidence).
- Pearson denominator is "rows where BOTH confidence AND success are non-null" — `--stub` rows with `success: null` (no judge) are dropped.
- `mean cost: n/a` when all rows have `cost_usd = None` (stub mode; CONTEXT D-11).
- `conf_corr_r` field name is exact — M5-VALIDATION row `pearson-correlation` greps this string.
- Markdown shape is fixed-field allowlist per D-02; no row interpolation from raw model output (security: §"Eval accidentally committing secrets").

---

### `tests/eval/test_suite_loads.py` (NEW) — Wave 0

**Analog:** `tests/parser/test_examples.py:1-30` — directory-walk + name-set assertion.

**Target shape:**
```python
"""M5 D-05: suite loader finds all 5 golden fixtures."""
from pathlib import Path
import pytest
from voss.eval.suite import load_suite

EXPECTED = {"01-analyze", "02-plan-only", "03-approved-edit", "04-validation", "05-resume"}
SUITE_ROOT = Path(__file__).resolve().parent / "golden"


def test_suite_finds_five_fixtures():
    tasks = load_suite(SUITE_ROOT, suite="")  # SUITE_ROOT itself is the suite dir
    ids = {tid for tid, _ in tasks}
    assert ids == EXPECTED, f"missing or extra fixtures: {ids ^ EXPECTED}"


def test_each_task_parses():
    tasks = load_suite(SUITE_ROOT, suite="")
    for tid, spec in tasks:
        assert spec.prompt
        assert spec.rubric
        assert spec.mode in {"plan", "edit", "auto"}
```

**Adaptation notes:**
- `SUITE_ROOT` is `tests/eval/golden/` (resolved relative to this test file).
- `load_suite(suite_root, suite="")` — pass empty so suite_root is treated as the directory itself; alternative: pass `suite_root.parent` and `suite="golden"`. Pick the form that matches the implementation chosen in `suite.py`.

---

### `tests/eval/test_task_spec.py` (NEW) — Wave 0

**Analog:** `tests/harness/test_agent_integration.py` (pydantic round-trip + ValidationError assertion).

**Target shape:**
```python
"""M5 D-07: TaskSpec rejects unknown keys; validates mode + judge_inputs."""
import pytest
from pydantic import ValidationError
from voss.eval.suite import TaskSpec


def test_minimal_spec():
    spec = TaskSpec(prompt="x", mode="plan", rubric="PASS if ok")
    assert spec.judge_inputs == ["final", "file_diff"]
    assert spec.auto_approve_edits is False


def test_invalid_mode():
    with pytest.raises(ValidationError):
        TaskSpec(prompt="x", mode="rust", rubric="...")


def test_unknown_key_rejected():
    """ConfigDict(extra='forbid') guards against task.toml schema drift."""
    with pytest.raises(ValidationError):
        TaskSpec(prompt="x", mode="plan", rubric="...", typo_field=1)


def test_auto_approve_edits_round_trip():
    spec = TaskSpec(prompt="x", mode="edit", rubric="...", auto_approve_edits=True)
    assert spec.auto_approve_edits is True
```

**Adaptation notes:**
- M5-VALIDATION row `task-spec-model` requires unknown-key rejection — pin via `extra="forbid"` test.
- Test `auto_approve_edits` round-trip explicitly (task 03 depends on this field).

---

### `tests/eval/test_fixture_isolation.py` (NEW) — Wave 0

**Analog:** `tests/examples/helpers.py:60-69` (`run_voss` subprocess) + `tests/harness/test_session.py` (tmp_path pattern).

**Target shape:**
```python
"""M5 D-06: each run gets fresh tempdir + git init; no shared state across runs."""
from pathlib import Path
import pytest
from voss.eval.runner import _prepare_fixture


def test_prepare_fixture_creates_git_repo(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "fixture").mkdir()
    (src / "fixture" / "hello.txt").write_text("hi\n")
    cwd = _prepare_fixture(src, tmp_path / "run0")
    assert (cwd / ".git").is_dir()
    assert (cwd / "hello.txt").read_text() == "hi\n"


def test_two_runs_dont_share_state(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "fixture").mkdir()
    (src / "fixture" / "f.txt").write_text("a\n")
    a = _prepare_fixture(src, tmp_path / "run-a")
    b = _prepare_fixture(src, tmp_path / "run-b")
    (a / "f.txt").write_text("CHANGED\n")
    assert (b / "f.txt").read_text() == "a\n"
```

**Adaptation notes:**
- Tests the `_prepare_fixture` helper directly (in-process; no subprocess overhead).
- The `git init` requires `git` on PATH — CI already has it (M1 doctor check).

---

### `tests/eval/test_judge_verdict.py` (NEW) — Wave 1

**Analog:** `tests/harness/test_agent_integration.py:21-50` (FakeProvider pattern with canned response_format reply).

**Target shape:**
```python
"""M5 D-09: judge_run returns Verdict on valid JSON; ParseError → skipped."""
import asyncio
import pytest
from voss.eval.judge import Verdict, judge_run
from voss_runtime.providers.base import ProviderResponse


class FakeJudgeProvider:
    def __init__(self, verdict: Verdict | None):
        self.verdict = verdict

    async def complete(self, *, messages, model, response_format=None, **kw):
        text = self.verdict.model_dump_json() if self.verdict else "{}"
        return ProviderResponse(
            text=text, model=model, prompt_tokens=1, completion_tokens=1,
            cost_usd=0.0, raw={}, parsed=self.verdict,
        )

    def count_tokens(self, *, text, model):
        return 1


def test_judge_returns_verdict():
    fp = FakeJudgeProvider(Verdict(verdict="pass", confidence=0.9, rationale="ok"))
    verdict, vstr = asyncio.run(judge_run(
        provider=fp, model="m", task_prompt="t", final="f", file_diff="", rubric="r"
    ))
    assert vstr == "pass"
    assert verdict.confidence == 0.9


def test_judge_parse_error_returns_skipped():
    """RESEARCH §Pattern 2 fallback: ParseError → skipped."""
    from voss_runtime.providers.litellm_provider import ParseError

    class RaisingProvider:
        async def complete(self, **kw):
            raise ParseError("bad json")
        def count_tokens(self, **kw):
            return 1

    verdict, vstr = asyncio.run(judge_run(
        provider=RaisingProvider(), model="m", task_prompt="t", final="f",
        file_diff="", rubric="r"
    ))
    assert verdict is None
    assert vstr == "skipped"
```

**Adaptation notes:**
- `FakeJudgeProvider` shape mirrors `FakeProvider` in tests/harness/test_agent_integration.py.
- `ParseError` import path from `voss_runtime.providers.litellm_provider` (confirmed at litellm_provider.py:50).

---

### `tests/eval/test_judge_skipped.py` (NEW) — Wave 1

**Analog:** Same FakeProvider pattern; tests the agent-crashed path.

**Target shape:**
```python
"""M5 D-08: when agent run crashes, judge is never invoked; row has judge_verdict='skipped'."""
import asyncio
from voss.eval.runner import _drive_task
from voss.eval.suite import TaskSpec


class CrashingProvider:
    async def complete(self, **kw):
        raise RuntimeError("simulated agent crash")
    def count_tokens(self, **kw):
        return 1


def test_crashed_run_returns_crashed_true(tmp_path):
    spec = TaskSpec(prompt="x", mode="plan", rubric="...")
    cwd = tmp_path
    record, final, crashed = asyncio.run(_drive_task(
        "01-analyze", spec, cwd, provider=CrashingProvider(), model="m",
        permissions=None,
    ))
    assert crashed is True
    assert final == ""
```

**Adaptation notes:**
- Confirms `_drive_task` returns `crashed=True` on exception; runner skips judge call in that branch.
- Smaller scope than test_judge_verdict — focuses on the crash-path branch in runner.py.

---

### `tests/eval/test_cli_options.py` (NEW) — Wave 2

**Analog:** `tests/cli/test_run.py:22-58` (CliRunner + monkeypatch).

**Target shape:**
```python
"""M5 D-01: voss eval Click options surface."""
from click.testing import CliRunner
from voss.harness.cli import eval_cmd


def test_eval_help_lists_all_options():
    runner = CliRunner()
    result = runner.invoke(eval_cmd, ["--help"])
    assert result.exit_code == 0
    for flag in ("--suite", "--stub", "--live", "-k", "--out", "--judge-model", "--task", "--auth"):
        assert flag in result.output, f"missing flag: {flag}"


def test_eval_default_suite():
    runner = CliRunner()
    result = runner.invoke(eval_cmd, ["--help"])
    assert "golden" in result.output  # default value visible in help
```

**Adaptation notes:**
- Pure surface test; no actual eval invocation (that's `test_voss_eval_stub.py`).
- Pinned by M5-VALIDATION row `cli-eval-command`.

---

### `tests/eval/test_voss_eval_stub.py` (NEW) — Wave 2

**Analog:** `tests/examples/helpers.py:60-69` (`run_voss`) + `tests/harness/test_session_redaction.py` (JSON shape allowlist).

**Target shape:**
```python
"""M5 D-04, D-11: voss eval --stub produces JSONL with D-04 schema; cost_usd=null."""
import json
import subprocess
import sys
from pathlib import Path
import pytest

REQUIRED_FIELDS = {
    "task_id", "run_idx", "success", "cost_usd", "confidence", "duration_s",
    "judge_verdict", "judge_confidence", "judge_rationale", "provider",
    "model", "judge_model", "seed", "voss_version", "started_at",
}


def _run_eval(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "voss.cli", "eval", *args],
        cwd=cwd, capture_output=True, text=True, timeout=120,
    )


def test_stub_smoke_produces_jsonl(tmp_path):
    """End-to-end: --stub --task 02-plan-only -k 1 → 1 row matching D-04."""
    out = tmp_path / "eval-out"
    result = _run_eval(
        ["--stub", "--task", "02-plan-only", "-k", "1", "--out", str(out)],
        cwd=Path(__file__).resolve().parents[2],  # repo root
    )
    assert result.returncode == 0, result.stderr
    jsonl = out / "runs.jsonl"
    assert jsonl.exists()
    rows = [json.loads(line) for line in jsonl.read_text().splitlines() if line.strip()]
    assert len(rows) == 1
    assert set(rows[0].keys()) >= REQUIRED_FIELDS


def test_cost_field_null_under_stub(tmp_path):
    """D-11: stub cost = null, NOT 0.0 or a token-count estimate."""
    out = tmp_path / "eval-out"
    _run_eval(
        ["--stub", "--task", "02-plan-only", "-k", "1", "--out", str(out)],
        cwd=Path(__file__).resolve().parents[2],
    )
    rows = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines() if line.strip()]
    assert rows[0]["cost_usd"] is None


# Keyword-matchable tests for the 5 fixtures (per M5-VALIDATION rows task-01..task-05):
@pytest.mark.parametrize("tid", ["01-analyze", "02-plan-only", "03-approved-edit",
                                  "04-validation", "05-resume"])
def test_task_runs_under_stub(tmp_path, tid):
    """One run per fixture under stub; verifies fixture is parseable + driveable."""
    out = tmp_path / f"eval-{tid}"
    result = _run_eval(
        ["--stub", "--task", tid, "-k", "1", "--out", str(out)],
        cwd=Path(__file__).resolve().parents[2],
    )
    # Stub mode + no judge creds → judge_verdict = "skipped", success = null.
    assert result.returncode == 0, result.stderr
```

**Adaptation notes:**
- `REQUIRED_FIELDS` set is the D-04 allowlist — pinned by M5-VALIDATION row `stub-eval-smoke`.
- Parametrize names `task_01`, `task_02`, ... match M5-VALIDATION `-k task_NN` keyword runs (use `tid` directly and let pytest derive nodeid).
- Uses subprocess to test the real CLI dispatch path (mirror of `tests/examples/helpers.py:run_voss`).

---

### `tests/eval/test_live_signals.py` (NEW, `@pytest.mark.live`) — Wave 2

**Analog:** Existing `@pytest.mark.live` tests under `tests/harness/`.

**Target shape:**
```python
"""M5 EVAL-03/04: live provider populates cost_usd + confidence in JSONL."""
import json
import os
import subprocess
import sys
from pathlib import Path
import pytest

pytestmark = pytest.mark.live


def _has_creds() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY"))


@pytest.mark.skipif(not _has_creds(), reason="no provider creds")
def test_cost(tmp_path):
    out = tmp_path / "eval-out"
    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "eval",
         "--task", "02-plan-only", "-k", "1", "--out", str(out)],
        cwd=Path(__file__).resolve().parents[2],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0, result.stderr
    rows = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines() if line.strip()]
    assert rows[0]["cost_usd"] is not None
    assert rows[0]["cost_usd"] >= 0.0


@pytest.mark.skipif(not _has_creds(), reason="no provider creds")
def test_confidence(tmp_path):
    out = tmp_path / "eval-out"
    subprocess.run(
        [sys.executable, "-m", "voss.cli", "eval",
         "--task", "02-plan-only", "-k", "1", "--out", str(out)],
        cwd=Path(__file__).resolve().parents[2], check=True, timeout=300,
    )
    rows = [json.loads(line) for line in (out / "runs.jsonl").read_text().splitlines() if line.strip()]
    assert rows[0]["confidence"] is not None
    assert 0.0 <= rows[0]["confidence"] <= 1.0
```

**Adaptation notes:**
- `pytestmark = pytest.mark.live` at module level (existing pattern in repo).
- `@pytest.mark.skipif(not _has_creds())` ensures CI without creds skips cleanly.

---

### `tests/eval/test_pearson.py` (NEW) — Wave 3

**Analog:** None — pure stdlib reference test.

**Target shape:**
```python
"""M5 D-15 / EVAL-04: Pearson r computed via statistics.correlation, n=count of valid pairs."""
import statistics
from voss.eval.summary import _pearson


def test_pearson_matches_reference():
    rows = [
        {"confidence": 0.9, "success": True},
        {"confidence": 0.7, "success": True},
        {"confidence": 0.3, "success": False},
        {"confidence": 0.5, "success": False},
    ]
    r, n = _pearson(rows)
    expected = statistics.correlation([0.9, 0.7, 0.3, 0.5], [1.0, 1.0, 0.0, 0.0])
    assert r == pytest.approx(expected)
    assert n == 4


def test_pearson_drops_null_rows():
    rows = [
        {"confidence": 0.9, "success": True},
        {"confidence": None, "success": True},
        {"confidence": 0.5, "success": None},
    ]
    r, n = _pearson(rows)
    assert n == 1
    assert r is None  # n < 2


def test_pearson_constant_returns_none():
    """statistics.correlation raises on constant input — guard returns None."""
    rows = [
        {"confidence": 0.5, "success": True},
        {"confidence": 0.5, "success": True},
    ]
    r, n = _pearson(rows)
    assert r is None
```

**Adaptation notes:**
- Need `import pytest` for `pytest.approx`.
- `statistics.correlation` is stdlib at 3.10+; pyproject pins 3.11+ (RESEARCH §Standard Stack).
- Constant-input guard prevents `StatisticsError` (RESEARCH §Assumption A6).

---

### `tests/eval/test_summary_md.py` (NEW) — Wave 3

**Analog:** `tests/harness/test_recorder.py` (string-content assertion on generated artifact).

**Target shape:**
```python
"""M5 D-02: summary.md aggregates JSONL into required sections."""
import json
from pathlib import Path
from voss.eval.summary import write_summary


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n")


def test_summary_has_required_sections(tmp_path):
    rows = [
        {"task_id": "01-analyze", "run_idx": 0, "success": True, "cost_usd": 0.01,
         "confidence": 0.9, "judge_verdict": "pass", "provider": "Anthropic",
         "model": "claude-sonnet"},
        {"task_id": "02-plan-only", "run_idx": 0, "success": False, "cost_usd": 0.02,
         "confidence": 0.4, "judge_verdict": "fail", "provider": "Anthropic",
         "model": "claude-sonnet"},
    ]
    jsonl = tmp_path / "runs.jsonl"
    _write_rows(jsonl, rows)
    out = write_summary(jsonl, tmp_path / "summary.md")
    text = out.read_text()
    assert "overall success rate" in text
    assert "mean cost" in text
    assert "conf_corr_r" in text
    assert "01-analyze" in text
    assert "02-plan-only" in text
```

**Adaptation notes:**
- M5-VALIDATION row `markdown-summary-shape` requires per-task rate + cost + correlation + provider/model.
- `conf_corr_r` is the exact field name — grep-matches the pearson test.

---

### `tests/eval/test_gitignore.py` (NEW) — Wave 3

**Analog:** `voss/harness/cognition.py:575-582` (`write_voss_gitignore` source of truth).

**Reference excerpt** (cognition.py:575-582):
```python
def write_voss_gitignore(cwd: Path) -> bool:
    """Write `.voss/.gitignore` preserve-if-exists."""
    target = voss_dir(cwd) / ".gitignore"
    voss_dir(cwd).mkdir(parents=True, exist_ok=True)
    if target.exists():
        return False
    target.write_text("# voss session state and rebuildable cache\nsessions/\n")
    return True
```

**Target shape:**
```python
"""M5 D-03 / M2 D-09: .voss/.gitignore does NOT add eval/; .voss/eval/<ts>/ stays tracked."""
from pathlib import Path
from voss.harness.cognition import write_voss_gitignore


def test_voss_gitignore_does_not_ignore_eval(tmp_path):
    write_voss_gitignore(tmp_path)
    content = (tmp_path / ".voss" / ".gitignore").read_text()
    assert "eval/" not in content
    assert "eval" not in content.split() or content.split() == ["sessions/"]  # only sessions/


def test_voss_gitignore_still_ignores_sessions(tmp_path):
    """Regression guard: M2 D-09 sessions/ ignore preserved."""
    write_voss_gitignore(tmp_path)
    content = (tmp_path / ".voss" / ".gitignore").read_text()
    assert "sessions/" in content
```

**Adaptation notes:**
- Pinned by M5-VALIDATION row `voss-eval-gitignore`.
- Source-of-truth check: if anyone adds `eval/` to cognition.py:581 by mistake, this test fails.

---

### `tests/eval/golden/01-analyze/` (NEW) — Wave 4

**Analog:** `voss/harness/cognition.py:bootstrap_prompt` (analyze prompt surface).

**`task.toml`:**
```toml
# 01-analyze — analyze a tiny seed repo, expect .voss/architecture.md written.
prompt = "Analyze this repository and write architecture.md describing what it does."
mode = "edit"
rubric = """
PASS if:
- A file named .voss/architecture.md exists after the run.
- The file is non-empty and contains at least one paragraph describing the codebase.

FAIL if:
- .voss/architecture.md does not exist.
- The file is empty or contains only placeholder text.
"""
judge_inputs = ["final", "file_diff"]
auto_approve_edits = true
```

**`fixture/` contents:** A minimal seed repo (e.g., `main.py` with a 10-line "Hello" CLI, `README.md` with one paragraph). Keep < 200 LOC total.

**Adaptation notes:**
- `mode = "edit"` + `auto_approve_edits = true` → runner constructs `PermissionGate(mode="edit", auto_yes=True)` per permissions.py:98-104.
- Per RESEARCH §Open Question 2: measure the LLM agent path, NOT the deterministic `_handle_analyze` skill.
- Fixture seed must be small enough that a single turn can analyze it.

---

### `tests/eval/golden/02-plan-only/` (NEW) — Wave 4

**Analog:** M1 D-07 plan-mode contract + `voss/harness/permissions.py:108-109` (`mode == "plan"` denies non-read tools).

**`task.toml`:**
```toml
# 02-plan-only — plan a small code change in plan mode; expect non-empty plan, no writes.
prompt = "Add type hints to the add() function in calc.py. Plan only — do not write."
mode = "plan"
rubric = """
PASS if:
- The plan describes specific tool calls (e.g., fs_read calc.py, fs_write with type hints).
- No file modifications occurred in the fixture during the run.

FAIL if:
- The plan is empty or boilerplate.
- Any file in the fixture was modified.
"""
judge_inputs = ["final", "file_diff"]
```

**`fixture/`:** `calc.py` with a 5-line `def add(a, b): return a + b` (no type hints).

**Adaptation notes:**
- `mode = "plan"` → runner constructs `PermissionGate(mode="plan", auto_yes=False)`. Permissions gate denies non-read tools per permissions.py:108-109.
- Judge relies on `file_diff` being empty to confirm "no writes occurred".

---

### `tests/eval/golden/03-approved-edit/` (NEW) — Wave 4

**Analog:** `voss/harness/permissions.py:98-104` (auto_yes path).

**`task.toml`:**
```toml
# 03-approved-edit — apply an edit in edit mode with auto-approve; expect target file modified.
prompt = "Rename the function add() to sum_two() in calc.py and update its single call site in main.py."
mode = "edit"
rubric = """
PASS if:
- calc.py defines sum_two() (not add()).
- main.py imports and calls sum_two() (not add()).
- Both files were modified.

FAIL if:
- Either file is unchanged.
- The rename is incomplete (one file updated, the other not).
"""
judge_inputs = ["final", "file_diff"]
auto_approve_edits = true
```

**`fixture/`:** `calc.py` with `def add(a, b): return a + b` + `main.py` with `from calc import add; print(add(1, 2))`.

**Adaptation notes:**
- `auto_approve_edits = true` → runner wires `PermissionGate(auto_yes=True)`; no human prompt fires (RESEARCH §Pattern 3 Option A).
- Judge inspects `file_diff` (git diff of fixture cwd) to verify both files changed.

---

### `tests/eval/golden/04-validation/` (NEW) — Wave 4

**Analog:** `samples/classify.voss` (minimal sample for `voss check`).

**`task.toml`:**
```toml
# 04-validation — invoke `voss check` on a .voss sample inside the fixture; expect exit 0.
prompt = "Run `voss check sample.voss` in this directory and report the exit code."
mode = "edit"
rubric = """
PASS if:
- The agent's final answer indicates `voss check` exited 0.
- No errors or warnings reported.

FAIL if:
- The final answer indicates a non-zero exit code.
- The agent did not actually invoke voss check.
"""
judge_inputs = ["final"]
auto_approve_edits = true
```

**`fixture/`:** `sample.voss` — a copy of `samples/classify.voss` (minimal valid program).

**Adaptation notes:**
- `judge_inputs = ["final"]` — no file_diff needed; the agent's shell_run output captures the exit code.
- Uses shell_run tool (mode=edit + auto_yes=True allows it).

---

### `tests/eval/golden/05-resume/` (NEW) — Wave 4

**Analog:** RESEARCH §Pattern 4 (asyncio.Task.cancel + SessionRecord.save/load) + `voss/harness/session.py:133-192`.

**`task.toml`:**
```toml
# 05-resume — spawn a session, kill mid-turn, resume; expect prior-context surfaces.
prompt = "Summarize the contents of notes.txt."
mode = "plan"
rubric = """
PASS if:
- After resume, the agent's final answer summarizes notes.txt (not a fresh question).
- The summary references content present in notes.txt.
- The session record shows two turns (initial + resumed).

FAIL if:
- The agent restarts the task from scratch after resume.
- The session record shows only one turn.
- The summary references content not present in notes.txt.
"""
judge_inputs = ["final"]
```

**`fixture/`:** `notes.txt` with a few paragraphs of distinguishable content.

**Adaptation notes:**
- Runner detects `task_id.startswith("05-resume")` and switches to `_drive_resume` (RESEARCH §Pattern 4).
- `asyncio.sleep(0.05)` between spawn and `task.cancel()` lets the first tool dispatch begin (RESEARCH §Assumption A2: CancelledError propagates past `except Exception` because it's a BaseException in 3.8+).
- Independence from task 04 (D-06: no shared tempdir).

---

### `tests/packaging/test_wheel_install.py` (NEW, `@pytest.mark.slow`) — Wave 5

**Analog:** `tests/packaging/test_entrypoint.py:65-105` (`test_editable_install_exposes_voss_help`) — venv pattern; swap `-e .` for `<wheel>` and add doctor/import/samples asserts.

**Reference excerpt** (test_entrypoint.py:65-105):
```python
@pytest.mark.slow
def test_editable_install_exposes_voss_help(tmp_path):
    venv_dir = tmp_path / "venv"
    subprocess.run(
        [sys.executable, "-m", "venv", "--system-site-packages", str(venv_dir)],
        check=True, timeout=60,
    )
    venv_python = venv_dir / "bin" / "python"
    if not venv_python.exists():
        venv_python = venv_dir / "Scripts" / "python.exe"
    subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-q", "--no-deps", "-e", str(_repo_root())],
        check=True, timeout=300,
    )
    ...
    voss_bin = venv_dir / "bin" / "voss"
    if not voss_bin.exists():
        voss_bin = venv_dir / "Scripts" / "voss.exe"
    assert voss_bin.exists()
    bin_help = subprocess.run([str(voss_bin), "--help"], capture_output=True, text=True, timeout=30)
    assert bin_help.returncode == 0, bin_help.stderr
    assert "compile" in bin_help.stdout
```

**Target shape** (per RESEARCH §Pattern 6 + CONTEXT D-16):
```python
"""M5 EVAL-05 / D-16: build wheel, install in temp venv, smoke the post-install CLI surface."""
import shutil
import subprocess
import sys
from pathlib import Path
import pytest

from tests.packaging.test_entrypoint import _repo_root  # reuse helper


@pytest.mark.slow
def test_wheel_builds(tmp_path):
    """D-16 part 1: python -m build --wheel produces a wheel."""
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(_repo_root())],
        check=True, timeout=600,
    )
    wheels = list(dist.glob("voss-*.whl"))
    assert len(wheels) == 1, f"expected 1 wheel, got {wheels}"


@pytest.mark.slow
def test_install(tmp_path):
    """D-16 part 2: pip install <wheel> succeeds (with deps, unlike editable test)."""
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(_repo_root())],
        check=True, timeout=600,
    )
    wheel = next(dist.glob("voss-*.whl"))
    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, timeout=60)
    py = venv_dir / "bin" / "python"
    if not py.exists():
        py = venv_dir / "Scripts" / "python.exe"
    subprocess.run(
        [str(py), "-m", "pip", "install", "-q", str(wheel)],
        check=True, timeout=600,
    )


@pytest.mark.slow
def test_smoke_asserts(tmp_path):
    """D-16 part 3: in tempvenv, exercise the post-install CLI surface."""
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist), str(_repo_root())],
        check=True, timeout=600,
    )
    wheel = next(dist.glob("voss-*.whl"))
    venv_dir = tmp_path / "venv"
    subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True, timeout=60)
    py = venv_dir / "bin" / "python"
    if not py.exists():
        py = venv_dir / "Scripts" / "python.exe"
    subprocess.run([str(py), "-m", "pip", "install", "-q", str(wheel)], check=True, timeout=600)

    voss_bin = venv_dir / "bin" / "voss"
    if not voss_bin.exists():
        voss_bin = venv_dir / "Scripts" / "voss.exe"
    assert voss_bin.exists()

    repo = _repo_root()
    # voss --help
    r = subprocess.run([str(voss_bin), "--help"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr

    # voss compile samples/classify.voss (cwd=repo to find samples)
    r = subprocess.run([str(voss_bin), "compile", "samples/classify.voss"],
                       capture_output=True, text=True, timeout=60, cwd=repo)
    assert r.returncode == 0, r.stderr

    # voss check samples/classify.voss
    r = subprocess.run([str(voss_bin), "check", "samples/classify.voss"],
                       capture_output=True, text=True, timeout=60, cwd=repo)
    assert r.returncode == 0, r.stderr

    # voss doctor — RESEARCH §Common Pitfalls: in clean tempvenv, no creds → exit may be 0 or 1.
    # Accept exit ∈ {0, 1} and assert it terminates with diagnostic output (M1 D-13 posture).
    r = subprocess.run([str(voss_bin), "doctor"], capture_output=True, text=True, timeout=30)
    assert r.returncode in {0, 1}, f"voss doctor crashed: {r.stderr}"
    assert "python" in r.stdout.lower() or "provider" in r.stdout.lower()

    # import voss_runtime
    r = subprocess.run([str(py), "-c", "import voss_runtime"],
                       capture_output=True, text=True, timeout=30)
    assert r.returncode == 0, r.stderr
```

**Adaptation notes:**
- Drop `--no-deps` (RESEARCH §Anti-Patterns: smoke proves wheel installs WITH deps).
- Drop `--system-site-packages` (RESEARCH §Anti-Patterns: smoke validates an isolated venv).
- `voss doctor` exit-code check accepts `{0, 1}` per RESEARCH §Common Pitfalls: missing creds in tempvenv may FAIL the provider-auth row → exit 1; that's the loud-failure posture (M1 D-13), not a crash.
- `cwd=repo` for `voss compile samples/classify.voss` because the wheel installs the binary but not the repo samples (RESEARCH §Common Pitfalls).
- `_repo_root` helper reused from existing `tests/packaging/test_entrypoint.py`.

---

### `tests/packaging/test_readme.py` (NEW) — Wave 5

**Analog:** `tests/cli/test_check.py:70-97` (string-content assert pattern).

**Target shape:**
```python
"""M5 D-18: README install section contains required content."""
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _readme() -> str:
    return (REPO_ROOT / "README.md").read_text()


def test_pip_install_voss_present():
    """D-18: install command uses `pip install voss` (not `pip install -e ".[dev]"`)."""
    text = _readme()
    assert "pip install voss" in text


def test_voss_doctor_first_run_mentioned():
    """D-18: README directs users to run `voss doctor` after install."""
    assert "voss doctor" in _readme()


def test_samples_link_present():
    """D-18: README links to samples/."""
    text = _readme()
    assert "samples/" in text or "samples](" in text


def test_v01_framing_line_present():
    """D-18: v0.1 framing — 'Python harness; Rust later' (no Rust install path in v0.1)."""
    text = _readme()
    assert "Python harness" in text or "python harness" in text


def test_no_rust_install_path():
    """D-18: NO Rust install path in v0.1 docs. 'later' note OK; install instructions NOT OK."""
    text = _readme()
    # Permit phrases like "Rust later" or "(Rust shell later)" but reject install commands.
    assert "cargo install" not in text
    assert "brew install voss" not in text  # Homebrew deferred
```

**Adaptation notes:**
- M5-VALIDATION row `readme-install-polish` pins these exact strings.
- The "no Rust install path" test allows mention-as-future-note but rejects actual install commands.

---

### `README.md` (MODIFY) — Wave 5 D-18

**Analog:** Self. Existing install section.

**Target additions** (per CONTEXT D-18):
- Replace any "Not on PyPI yet" or `pip install -e ".[dev]"` install instructions with `pip install voss`.
- Add a "First run: `voss doctor`" line directly after the install command.
- Add a "v0.1 is a Python harness; Rust shell later" framing line near the top.
- Add a link to `samples/` directory and a link to the harness commands section.
- Remove (or move to a "Roadmap" footer) any Rust/Homebrew install instructions; a single sentence "Rust + Homebrew distribution post-v0.1" is acceptable.

**Adaptation notes:**
- Required content pinned by M5-VALIDATION row `readme-install-polish` and `test_readme.py` (above).
- Keep style consistent with the existing README (don't rewrite tone; surgical edit per CLAUDE.md §3).

---

## Shared Patterns

### Pattern A: Pydantic `response_format=Pydantic` JSON-mode (judge + Plan)
**Source:** `voss_runtime/providers/litellm_provider.py:32-50`.
**Apply to:** `voss/eval/judge.py:judge_run` (Verdict response).
**Critical:** `LiteLLMProvider.complete` already calls `response_format.model_validate_json(text)` and raises `ParseError` on failure. Eval catches `ParseError` and marks `judge_verdict = "skipped"` (RESEARCH §Pattern 2).

### Pattern B: `PermissionGate(auto_yes=True)` for non-interactive runs
**Source:** `voss/harness/permissions.py:98-104` (existing `auto_yes` bool).
**Apply to:** `voss/eval/runner.py:_drive_task` when `spec.auto_approve_edits is True` (task 03).
**Critical:** Use Option A from RESEARCH §Pattern 3 — construct the gate in-process; no env-var bridge needed. The gate's existing `needs_prompt` short-circuits on `auto_yes` (permissions.py:103-105).

### Pattern C: Per-run hermetic git tempdir
**Source:** RESEARCH §Code Examples + tests/examples/helpers.py:_temp_project pattern (M3).
**Apply to:** `voss/eval/runner.py:_prepare_fixture` + `tests/eval/test_fixture_isolation.py`.
**Behavior:** `shutil.copytree(task_dir/"fixture", tmp/"fixture") → git init -b main → git commit -m init`. Provides a clean diff baseline for the judge's `file_diff` input.

### Pattern D: Loud-failure on missing prerequisites
**Source:** M1 D-13, M2 D-07, M3 D-02, M4 D-10 — all use `click.echo(..., err=True) + sys.exit(2)`.
**Apply to:** `voss/eval/runner.py:run_suite` when `auth_mod.resolve(...).source == "none"` and `--stub` not passed.
**Critical:** Exact message from CONTEXT D-10: `"voss eval: no provider creds — pass --stub for hermetic smoke or run /login"`. Tests pin this string.

### Pattern E: JSONL fixed-field allowlist
**Source:** `voss/harness/session.py:60-77` (`RunRecord` dataclass — fixed fields, no `**kwargs`).
**Apply to:** `voss/eval/runner.py:_append_row` row construction.
**Critical:** Never spread untrusted dicts into the row. The 15 D-04 fields are the allowlist; security review (RESEARCH §Security Domain) requires this to prevent secret leakage via judge output.

### Pattern F: Stdlib-only Pearson via `statistics.correlation`
**Source:** RESEARCH §Pattern 5 (`from statistics import correlation`).
**Apply to:** `voss/eval/summary.py:_pearson`.
**Critical:** Wrap in `try/except StatisticsError` OR guard with `len(set(values)) < 2` — `correlation` raises on constant input (RESEARCH §Assumption A6). No scipy (RESEARCH §"Don't Hand-Roll").

### Pattern G: AGENT_COMMANDS tuple registration
**Source:** `voss/harness/cli.py:795-810`.
**Apply to:** Adding `eval_cmd` to AGENT_COMMANDS (Wave 2).
**Critical:** Append-only; do NOT touch the existing 8 entries. `register(main)` at line 807 picks it up.

### Pattern H: `tests/packaging` venv subprocess pattern
**Source:** `tests/packaging/test_entrypoint.py:65-105`.
**Apply to:** `tests/packaging/test_wheel_install.py`.
**Critical:** Swap `pip install -e .` for `pip install <wheel>`; drop `--no-deps`. The cross-platform `bin/voss` vs `Scripts/voss.exe` resolution is preserved.

---

## No Analog Found

| File | Role | Data Flow | Notes |
|------|------|-----------|-------|
| `tests/eval/test_pearson.py` | test (stdlib reference) | transform | No prior in-tree test of `statistics.correlation`. Greenfield 30-LOC test; uses `pytest.approx`. |

---

## Metadata

**Analog search scope:** `voss/`, `voss/harness/`, `voss_runtime/providers/`, `tests/`, `tests/eval/` (new), `tests/packaging/`, `samples/`, `README.md`, `.planning/phases/M2-project-cognition/M2-PATTERNS.md`, `.planning/phases/M3-language-validation/M3-PATTERNS.md`, `.planning/phases/M4-voss-authored-harness-loop/M4-PATTERNS.md`.

**Files scanned:** 28 (every analog explicitly read or cited from M5-RESEARCH file:line).

**Pattern extraction date:** 2026-05-11.

---

## PATTERN MAPPING COMPLETE

**Phase:** M5 — Eval and Distribution Prep
**Files classified:** 27
**Analogs found:** 27 / 27

### Coverage
- Files with exact analog: 17
- Files with role-match analog: 9
- Files with no analog: 1 (`tests/eval/test_pearson.py` — stdlib reference, 30 LOC)

### Key Patterns Identified
- **Every primitive eval needs already exists in the codebase.** `Plan.confidence` (agent.py:46), `RunRecord.cost_usd` (session.py:77), `LiteLLMProvider.complete response_format` (litellm_provider.py:32-50), `PermissionGate(auto_yes=True)` (permissions.py:98-104), `SessionRecord.save/load` (session.py:133-192), `AGENT_COMMANDS` tuple (harness/cli.py:795-810). Eval is wiring + orchestration, not new infrastructure.
- **`response_format=Pydantic` is the canonical JSON-mode shape.** `Plan` (agent.py) and `Verdict` (eval/judge.py) both ride the same `litellm_provider.py:32-50` machinery — single path, single failure mode (`ParseError`).
- **Three stdlib pieces cover the new-primitive surface.** `tomllib` (task.toml), `statistics.correlation` (Pearson r), `venv` (wheel smoke). Zero new top-level deps.
- **Auth `role` extension is a 1-line pass-through.** `voss/harness/auth.py:resolve(preference, role=None)` — `role` ignored in v0.1; future versions can branch on it. RESEARCH §Assumption A1.
- **JSONL is the canonical artifact; Markdown is human-only.** Fixed-field allowlist (D-04, 15 fields); never spread untrusted dicts. Future cross-version eval comparison reads JSONL.
- **Loud-failure no-creds posture mirrors M1/M2/M3/M4.** Exact message string `"voss eval: no provider creds — pass --stub for hermetic smoke or run /login"` pinned by D-10 + tests.

### File Created
`/Users/benjaminmarks/Projects/Voss/.planning/phases/M5-eval-and-distribution-prep/M5-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now produce wave-aligned PLAN.md files (Wave 0..5 per M5-VALIDATION) with per-file analog citations and concrete code excerpts. Every M5 file has an in-tree analog or in-file extension target; only `test_pearson.py` is greenfield (30 LOC stdlib reference).
