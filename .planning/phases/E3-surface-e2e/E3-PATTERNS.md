# Phase E3: Surface E2E - Pattern Map

**Mapped:** 2026-06-10
**Files analyzed:** 7 (2 modified, 5 new)
**Analogs found:** 7 / 7

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/eval/suite.py` | model | transform | `voss/eval/suite.py` (self, E1-01 `checks` field addition) | exact |
| `voss/eval/runner.py` | service | request-response + event-driven | `voss/eval/runner.py` (self, `_drive_task`/`_drive_resume`) + `tests/e2e/runner.py` | exact |
| `tests/eval/surfaces/<NN>-<slug>/task.toml` | config | — | `tests/eval/golden/03-approved-edit/task.toml` | exact |
| `tests/eval/surfaces/<NN>-<slug>/fixture/` | config | — | `tests/eval/golden/03-approved-edit/fixture/` | exact |
| `tests/eval/test_surface_drivers.py` | test | request-response + event-driven | `tests/harness/test_server_app.py` + `tests/e2e/runner.py` | role-match |
| `tests/eval/test_surface_suite_load.py` | test | batch | `tests/eval/test_suite_loads.py` | exact |
| `tests/eval/test_task_spec.py` (modified) | test | transform | `tests/eval/test_task_spec.py` (self) | exact |

---

## Pattern Assignments

### `voss/eval/suite.py` — add `surface` and `target_file` fields (model, transform)

**Analog:** `voss/eval/suite.py` — the E1-01 `checks` field addition is the direct precedent.

**Current schema pattern** (`/Users/benjaminmarks/Projects/Voss/voss/eval/suite.py`, lines 41–54):
```python
class TaskSpec(BaseModel):
    """Validated `task.toml` row. Mirrors M1 D-07 mode tiers + D-08 rubric shape."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(description="Prompt passed to `voss do`.")
    mode: Literal["plan", "edit", "auto"]
    rubric: str = Field(description="Plain-text PASS/FAIL criteria (D-08).")
    judge_inputs: list[Literal["final", "file_diff"]] = ["final", "file_diff"]
    provider: str | None = None
    model: str | None = None
    auto_approve_edits: bool = False
    tools: list[str] = Field(default_factory=list)
    checks: list[AnyCheck] = Field(default_factory=list)
```

**Fields to add — copy `checks` optional-with-default pattern:**
```python
    surface: Literal["internal", "cli:do", "cli:chat", "cli:edit", "serve"] = "internal"
    target_file: str | None = None  # required by cli:edit driver; None for all other surfaces
```

Key constraint: `extra="forbid"` is already present — new fields must be explicit model fields (not unknown keys), which is exactly how `checks` was added. Back-compat is guaranteed: golden tasks have no `surface` key → default `"internal"` → unchanged behavior.

---

### `voss/eval/runner.py` — surface dispatch + 4 driver functions (service, request-response + event-driven)

**Analog:** `voss/eval/runner.py` itself — `_drive_task` (lines 241–292) is the dispatch point to extend; `_drive_resume` (lines 182–238) is the model for an async helper that returns `(record, final, capped)`.

**Also analog:** `tests/e2e/runner.py` `CliRunner.run()` (lines 181–208) for subprocess invocation ergonomics.

**Imports already present in runner.py** (lines 1–35) — nothing new needed:
```python
import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
import httpx
```
E3 drivers need `import sys` and `import threading` added.

**`_live_env` helper — copy from RESEARCH.md Pattern 2, consistent with CliRunner.env() stripping logic (tests/e2e/runner.py lines 157–178):**
```python
def _live_env(cwd: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"
    env["VOSS_DEV"] = "1"
    env["PYDANTIC_DISABLE_PLUGINS"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    env["TRANSFORMERS_OFFLINE"] = "1"
    return env
```
Do NOT strip auth keys (contrast with CliRunner.env() which strips `ANTHROPIC_API_KEY`/`OPENAI_API_KEY` — that is the stub path; E3 live drivers inherit auth from caller env).

**`_drive_cli_do` — subprocess pattern from CliRunner.run() (tests/e2e/runner.py lines 181–208):**
```python
async def _drive_cli_do(spec: TaskSpec, cwd: Path, *, timeout: float = 120.0) -> tuple[str, str, bool]:
    """Returns (final, crash_reason_or_None, capped=False)."""
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "do", spec.prompt, "--plain"],
        cwd=str(cwd),
        env=_live_env(cwd),
        input="",              # empty stdin → isatty()=False, appends "" (harmless)
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return "", f"returncode={result.returncode}: {result.stderr[:200]}", False
    return result.stdout.strip(), None, False
```
Note: `input=""` not `stdin=subprocess.DEVNULL` — matches CliRunner.run() default (line 193–194: "Default to empty-string stdin so the harness's 'piped stdin' branch appends nothing").

**`_drive_cli_chat` — same subprocess skeleton, piped stdin for REPL:**
```python
async def _drive_cli_chat(spec: TaskSpec, cwd: Path, *, timeout: float = 120.0) -> tuple[str, str | None, bool]:
    import sys
    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "chat", "--plain"],
        cwd=str(cwd),
        env=_live_env(cwd),
        input=spec.prompt + "\n",   # single line → input() reads it → EOFError → clean exit
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return "", f"returncode={result.returncode}: {result.stderr[:200]}", False
    return result.stdout.strip(), None, False
```

**`_drive_cli_edit` — requires `target_file` on spec:**
```python
async def _drive_cli_edit(spec: TaskSpec, cwd: Path, *, timeout: float = 120.0) -> tuple[str, str | None, bool]:
    import sys
    if not spec.target_file:
        return "", "cli:edit requires target_file in task.toml", False
    target = cwd / spec.target_file
    result = subprocess.run(
        [sys.executable, "-m", "voss.cli", "edit", str(target), "--plain"],
        cwd=str(cwd),
        env=_live_env(cwd),
        input=spec.prompt + "\n",
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        return "", f"returncode={result.returncode}: {result.stderr[:200]}", False
    return result.stdout.strip(), None, False
```

**`_drive_serve` — async subprocess + httpx SSE, modeled on existing httpx usage in runner.py (lines 18, 154–178) and FAKE_TURN seam in app.py (lines 166–178):**
```python
async def _drive_serve(
    spec: TaskSpec,
    cwd: Path,
    *,
    permission_choice: str = "a",
    timeout: float = 180.0,
) -> tuple[str, str | None, bool]:
    import sys, threading, time as _time
    env = _live_env(cwd)
    proc = subprocess.Popen(
        [sys.executable, "-m", "voss.cli", "serve"],
        env=env, cwd=str(cwd),
        stdin=subprocess.PIPE,   # held open = heartbeat; EOF self-terminates server
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True, bufsize=1,
    )
    stderr_lines: list[str] = []
    threading.Thread(target=lambda: [stderr_lines.append(l) for l in proc.stderr], daemon=True).start()

    handshake = None
    deadline = _time.monotonic() + 60.0
    for line in proc.stdout:
        try:
            h = json.loads(line.strip())
            if h.get("token"):
                handshake = h
                break
        except json.JSONDecodeError:
            pass
        if _time.monotonic() > deadline:
            proc.kill()
            return "", f"handshake timeout; stderr: {''.join(stderr_lines[-10:])}", False

    base_url = f"http://127.0.0.1:{handshake['port']}"
    headers = {"Authorization": f"Bearer {handshake['token']}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(f"{base_url}/session",
                json={"cwd": str(cwd), "auth": "auto"}, headers=headers)
            r.raise_for_status()
            sid = r.json()["id"]

            final_text = ""
            async with client.stream("GET", f"{base_url}/session/{sid}/events",
                                     headers={**headers, "Accept": "text/event-stream"}) as sse:
                await client.post(f"{base_url}/session/{sid}/message",
                    json={"parts": [{"type": "text", "text": spec.prompt}], "mode": spec.mode},
                    headers=headers)

                event_type = ""
                async for line in sse.aiter_lines():
                    line = line.rstrip("\r")
                    if not line:
                        event_type = ""
                        continue
                    if line.startswith(":"):
                        continue
                    if line.startswith("event:"):
                        event_type = line[6:].strip()
                    elif line.startswith("data:"):
                        try:
                            payload = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        ev_type = payload.get("type", event_type)
                        if ev_type == "permission.updated":
                            await client.post(f"{base_url}/session/{sid}/permission",
                                json={"id": payload["id"], "choice": permission_choice},
                                headers=headers)
                        elif ev_type == "final":
                            final_text = payload.get("text", "")
                        elif ev_type == "session.idle":
                            break
    except Exception as exc:
        return "", f"{type(exc).__name__}: {str(exc)[:300]}", False
    finally:
        if proc.stdin:
            proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    return final_text, None, False
```

**`_drive_task` dispatch — replace the current task_id.startswith("05-") branch with surface dispatch (lines 255–292). Copy the existing `except Exception` + `finally` structure:**
```python
async def _drive_task(task_id, spec, *, cwd, provider, model, stub=False, max_turns=15):
    record = SessionRecord.new(cwd=cwd, model=_record_model(model), name=task_id)
    permissions = PermissionGate(mode=spec.mode, auto_yes=spec.auto_approve_edits)
    net_session = _make_stub_net_session(spec, stub=stub)
    capped = False
    try:
        surface = getattr(spec, "surface", "internal")
        if surface == "cli:do":
            final, crash_reason, capped = await _drive_cli_do(spec, cwd)
        elif surface == "cli:chat":
            final, crash_reason, capped = await _drive_cli_chat(spec, cwd)
        elif surface == "cli:edit":
            final, crash_reason, capped = await _drive_cli_edit(spec, cwd)
        elif surface == "serve":
            final, crash_reason, capped = await _drive_serve(spec, cwd)
        else:  # "internal" — existing path unchanged
            # ... existing run_turn / _drive_resume logic ...
```

**JSONL row extension — add `surface` as additive field after existing fields (lines 434–456), AND update `REQUIRED_FIELDS` in `tests/eval/test_voss_eval_stub.py` in the same plan:**
```python
row = {
    # ... all existing fields ...
    "gate_pass": gate_pass,
    "capped": capped,
    "checks": check_results,
    "surface": getattr(spec, "surface", "internal"),   # additive; E3 addition
}
```

---

### `tests/eval/surfaces/<NN>-<slug>/task.toml` (config)

**Analog:** `tests/eval/golden/03-approved-edit/task.toml` — the closest match: uses `mode = "edit"`, `auto_approve_edits = true`, `judge_inputs`, and `[[checks]]` blocks.

**Full analog** (`/Users/benjaminmarks/Projects/Voss/tests/eval/golden/03-approved-edit/task.toml`, lines 1–30):
```toml
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

[[checks]]
type = "file_contains"
path = "calc.py"
text = "sum_two"

[[checks]]
type = "file_contains"
path = "main.py"
text = "sum_two"

[[checks]]
type = "cmd"
run = "! grep -q 'def add(' calc.py"
```

**E3 surface scenario additions** — copy the above structure and add:
- `surface = "cli:do"` (or `"cli:chat"`, `"cli:edit"`, `"serve"`)
- `target_file = "calc.py"` for `cli:edit` scenarios only
- `auto_approve_edits = false` for `serve` permission-gate scenario (driver handles permission via `/permission`)

Fixture dirs mirror `tests/eval/golden/03-approved-edit/fixture/` — a minimal project with seed files (`calc.py`, `main.py`, or `hello.py` stub as appropriate). Git init is handled by `_prepare_fixture` in runner.py (lines 50–70) — fixture dir just needs the seed files.

---

### `tests/eval/test_surface_drivers.py` (test, request-response + event-driven)

**Analog:** `tests/harness/test_server_app.py` — covers the same SSE + permission flow using `TestClient`, `FAKE_TURN` seam, and monkeypatching. Also: `tests/e2e/runner.py` for subprocess invocation ergonomics. Also: `tests/eval/test_checks.py` for the import + direct-function-call test style.

**Imports pattern** — copy from `tests/harness/test_server_app.py` (lines 1–16) and `tests/eval/test_checks.py` (lines 1–8):
```python
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from voss.eval.runner import _drive_cli_do, _drive_cli_chat, _drive_cli_edit, _drive_serve
from voss.eval.suite import TaskSpec
```

**VOSS_DEV autouse** — already provided by `tests/eval/conftest.py` (lines 6–9). No need to re-add in the test file:
```python
# conftest.py already sets:
@pytest.fixture(autouse=True)
def _set_voss_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VOSS_DEV", "1")
```

**Stub CLI driver test pattern** — use a real subprocess pointing to `voss.cli` with env overrides. Mirror the `sitecustomize.py` injection pattern from `tests/e2e/runner.py` (lines 83–155) ONLY in tests (D-05 allows stub injection in tests, forbids it in live drivers):
```python
# From tests/e2e/runner.py CliRunner — use its stub env for driver unit tests
from tests.e2e.runner import CliRunner

@pytest.fixture
def stub_runner(tmp_path):
    return CliRunner(project_root=tmp_path / "proj", state_home=tmp_path / "state")

def test_cli_do_stub(stub_runner, tmp_path):
    """cli:do driver returns non-empty stdout against StubProvider."""
    cwd = stub_runner.project_root
    cwd.mkdir(parents=True, exist_ok=True)
    spec = TaskSpec(prompt="Say hello.", mode="plan", rubric="...", surface="cli:do")
    # Use asyncio.run for async driver; or monkeypatch env and use subprocess.run directly
    result = stub_runner.run("do", "Say hello.", "--plain")
    assert result.returncode == 0
    assert result.stdout.strip()
```

**VOSS_SERVE_FAKE_TURN stub test for serve driver** — set `VOSS_SERVE_FAKE_TURN=1` in subprocess env; server's `_run_turn` (app.py lines 165–178) emits a canned turn without a real provider. Pattern from `tests/harness/test_server_app.py` (lines 40–49):
```python
@pytest.fixture
def fake_turn_env(monkeypatch):
    """Set VOSS_SERVE_FAKE_TURN=1 so spawned serve subprocess uses canned turn."""
    monkeypatch.setenv("VOSS_SERVE_FAKE_TURN", "1")

def test_serve_stub(tmp_path, fake_turn_env):
    """serve driver: spawn server with FAKE_TURN, drive a turn, get final text."""
    import asyncio
    cwd = tmp_path / "proj"
    cwd.mkdir()
    spec = TaskSpec(prompt="hello", mode="plan", rubric="...", surface="serve")
    final, crash, capped = asyncio.run(_drive_serve(spec, cwd))
    assert crash is None
    assert "echo: hello" in final or "fake turn" in final.lower()
```

**Permission reply test** — same `fake_turn_env` fixture + a spec whose prompt triggers the fake gate path. Copy the `test_permission_reply_resolves_future` pattern (test_server_app.py lines 119–138) but over the full subprocess+SSE path:
```python
def test_serve_permission_allow_stub(tmp_path, fake_turn_env):
    import asyncio
    spec = TaskSpec(prompt="hello", mode="plan", rubric="...", surface="serve")
    final, crash, capped = asyncio.run(_drive_serve(spec, tmp_path / "proj", permission_choice="a"))
    assert crash is None
```

---

### `tests/eval/test_surface_suite_load.py` (test, batch)

**Analog:** `tests/eval/test_suite_loads.py` — exact same pattern: create tmp task dirs with `task.toml`, call `load_suite`, assert task ids.

**Full analog** (`/Users/benjaminmarks/Projects/Voss/tests/eval/test_suite_loads.py`, lines 1–50):
```python
from __future__ import annotations

from pathlib import Path

from voss.eval.suite import load_suite


def _write_task(root: Path, task_id: str, *, mode: str = "plan") -> None:
    task_dir = root / task_id
    task_dir.mkdir()
    (task_dir / "task.toml").write_text(
        "\n".join([
            f'prompt = "Prompt for {task_id}"',
            f'mode = "{mode}"',
            f'rubric = "PASS if {task_id} works"',
            "",
        ])
    )


def test_suite_finds_expected_fixtures(tmp_path: Path) -> None:
    tasks = load_suite(_suite_root(tmp_path), suite="")
    ids = [task_id for task_id, _ in tasks]
    assert ids == sorted(EXPECTED)
```

For E3's `test_surface_suite_load.py`, copy this pattern exactly but:
- Write task.tomls with `surface = "cli:do"` etc. fields
- Assert `load_suite(surfaces_dir, suite="")` finds them
- Assert `spec.surface` values are correct on loaded specs

---

### `tests/eval/test_task_spec.py` (modified — add surface field assertions)

**Analog:** `tests/eval/test_task_spec.py` itself — add new tests following the `test_checks_*` pattern (lines 39–125).

**Pattern to copy** (lines 39–42 — minimal optional field test):
```python
def test_checks_defaults_empty() -> None:
    spec = TaskSpec.model_validate({"prompt": "x", "mode": "plan", "rubric": "..."})
    assert spec.checks == []
```

**New tests to add following this pattern:**
```python
def test_surface_defaults_internal() -> None:
    spec = TaskSpec(prompt="x", mode="plan", rubric="...")
    assert spec.surface == "internal"

def test_surface_cli_do() -> None:
    spec = TaskSpec.model_validate({"prompt": "x", "mode": "plan", "rubric": "...", "surface": "cli:do"})
    assert spec.surface == "cli:do"

def test_surface_invalid_rejected() -> None:
    with pytest.raises(ValidationError):
        TaskSpec.model_validate({"prompt": "x", "mode": "plan", "rubric": "...", "surface": "bogus"})

def test_target_file_defaults_none() -> None:
    spec = TaskSpec(prompt="x", mode="plan", rubric="...")
    assert spec.target_file is None

def test_target_file_cli_edit() -> None:
    spec = TaskSpec.model_validate({
        "prompt": "x", "mode": "edit", "rubric": "...",
        "surface": "cli:edit", "target_file": "calc.py"
    })
    assert spec.target_file == "calc.py"
```

---

## Shared Patterns

### VOSS_DEV Gate (autouse in all eval tests)
**Source:** `tests/eval/conftest.py` (lines 6–9)
**Apply to:** `test_surface_drivers.py`, `test_surface_suite_load.py`
```python
@pytest.fixture(autouse=True)
def _set_voss_dev(monkeypatch: pytest.MonkeyPatch) -> None:
    """All eval tests run with VOSS_DEV=1 so the gated verb is accessible."""
    monkeypatch.setenv("VOSS_DEV", "1")
```
This is inherited automatically — no action needed in new test files if they live under `tests/eval/`.

### JSONL Row Sentinel (REQUIRED_FIELDS)
**Source:** `tests/eval/test_voss_eval_stub.py` (lines 11–31)
**Apply to:** Same file — add `"surface"` to the set in the SAME plan that adds `surface` to the row dict.
```python
REQUIRED_FIELDS = {
    "task_id", "run_idx", "success", "cost_usd", "confidence",
    "duration_s", "judge_verdict", "judge_confidence", "judge_rationale",
    "provider", "model", "judge_model", "live", "seed", "voss_version",
    "started_at", "gate_pass", "capped", "checks",
    # E3 addition:
    "surface",
}
```

### Fixture Preparation
**Source:** `voss/eval/runner.py` `_prepare_fixture` (lines 50–70) and `_file_diff` (lines 73–81)
**Apply to:** All surface driver implementations — they receive an already-prepared `cwd` from `run_suite`'s `with tempfile.TemporaryDirectory(...)` block (lines 372–373). Drivers do NOT call `_prepare_fixture` themselves; they receive the prepared `cwd`.
```python
# In run_suite (already wired):
with tempfile.TemporaryDirectory(prefix=f"voss-eval-{task_id}-") as tmp:
    cwd = _prepare_fixture(suite_root / task_id, Path(tmp))
    # ... driver dispatch uses this cwd ...
    diff = _file_diff(cwd)   # called AFTER driver returns, regardless of surface
```

### Exception-as-Row Pattern
**Source:** `voss/eval/runner.py` `_drive_task` exception handler (lines 287–291)
**Apply to:** All surface drivers — crash reason propagates to row; never re-raises.
```python
except Exception as exc:  # noqa: BLE001 - eval records failures as rows
    return record, "", f"{type(exc).__name__}: {str(exc)[:300]}", False
```
CLI and serve surface driver functions return `(final, crash_reason_or_None, capped)` tuples; the `_drive_task` wrapping logic converts `crash_reason != None` to the existing `crash_reason` path in `run_suite`.

### Subprocess Env for Stub Tests vs Live Drivers
**Source:** `tests/e2e/runner.py` `CliRunner.env()` (lines 157–178) vs E3's `_live_env()`
**Apply to:** All subprocess calls
- **In tests:** Use `CliRunner` (strips auth keys, injects `sitecustomize.py`, stub provider) — D-10 compliant (hermetic).
- **In live drivers (`_drive_cli_*`, `_drive_serve`):** Use `_live_env()` (inherits auth keys, no stub injection) — D-05 compliant (live).

---

## No Analog Found

All files have close analogs. No entries in this section.

---

## Metadata

**Analog search scope:** `voss/eval/`, `tests/eval/`, `tests/e2e/`, `tests/harness/`, `voss/harness/server/`
**Files scanned:** 13 source files read in full
**Pattern extraction date:** 2026-06-10
