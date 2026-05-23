# Phase F5: Commit with Critique Hook - Pattern Map

**Mapped:** 2026-05-22
**Files analyzed:** 3 (2 new, 1 modified)
**Analogs found:** 3 / 3

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `voss/harness/consensus.py` | service | request-response (single-shot LLM) | `voss/harness/agent.py` (`_record_run_call`) | exact — same provider.complete + Pydantic response_format pattern |
| `voss/harness/cli.py` | controller | request-response | `voss/harness/cli.py` (`skill_group`, `do_cmd`) | exact — same file; copy Click group + auth patterns from existing commands |
| `tests/harness/test_consensus.py` | test | request-response | `tests/harness/test_provider_response.py` + `tests/harness/test_cli.py` | role-match — same pytest + monkeypatch + CliRunner patterns |

---

## Pattern Assignments

### `voss/harness/consensus.py` (service, request-response)

**Primary analog:** `voss/harness/agent.py` — `_record_run_call` (lines 1404–1453)
**Secondary analog:** `voss/harness/code/config.py` (lines 40–58) for YAML loading
**Tertiary analog:** `voss/harness/recorder.py` (lines 430–443) for git subprocess

**Imports pattern** (copy from `voss/harness/agent.py` lines 8–18):
```python
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import click
import yaml
from pydantic import BaseModel, Field
```

**Pydantic model pattern** (copy structure from `voss/harness/agent.py` lines 196–211):
```python
# agent.py lines 196-211 — RunSemantics uses model_config extra="ignore"
# to silently drop hallucinated fields. CritiqueResponse must do the same.
class RunSemantics(BaseModel):
    model_config = {"extra": "ignore"}

    goal: str = ""
    avoided: list[dict] = Field(default_factory=list)
    # ...
```
Apply `model_config = {"extra": "ignore"}` to all three F5 Pydantic models
(`Violation`, `CritiqueSummary`, `CritiqueResponse`, `ConstraintsConfig`).

**Single-shot provider.complete pattern** (copy from `voss/harness/agent.py` lines 1415–1453):
```python
# agent.py lines 1415-1453 — THE pattern for single-shot provider.complete
try:
    resp = await provider.complete(
        messages=[
            {"role": "system", "content": RECORD_RUN_SYSTEM},
            {"role": "user", "content": transcript},
        ],
        model=model,
        response_format=RunSemantics,
        temperature=0.0,
        max_tokens=800,
    )
except Exception:  # noqa: BLE001 — sentinel-return is the contract
    # ... telemetry, then return None
    return None
# ...
if resp.parsed is None:
    return None
return resp.parsed
```
F5 adaptation: replace `RunSemantics` with `CritiqueResponse`, replace `return None`
with `click.echo(warning, err=True); sys.exit(0)` (fail-open per D-16), and add
`resp.parsed is None` guard before accessing violations.

**YAML safe_load pattern** (copy from `voss/harness/code/config.py` line 46):
```python
# code/config.py line 46
raw = yaml.safe_load(defaults_path.read_text(encoding="utf-8")) or {}
```
F5 adaptation: `raw = yaml.safe_load(constraints_path.read_text(encoding="utf-8")) or {}`
then `ConstraintsConfig.model_validate(raw)`.

**Git subprocess pattern** (copy from `voss/harness/recorder.py` lines 430–443):
```python
# recorder.py lines 430-443
def _git_diff_stat(cwd: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "diff", "--stat"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if out.returncode != 0:
        return ""
    return out.stdout[:4096]
```
F5 adaptation: replace `["git", "diff", "--stat"]` with `["git", "diff", "--cached"]`,
change timeout to 10, truncate at 30_000 chars, return empty string → exit 0 (no staged diff).

---

### `voss/harness/cli.py` — modifications (controller, request-response)

**Primary analog:** `voss/harness/cli.py` — `skill_group` (lines 2596–2708) and `AGENT_COMMANDS` (lines 3163–3188)

**Click group pattern** (copy from `voss/harness/cli.py` lines 2596–2601 and 2710–2712):
```python
# cli.py lines 2596-2598 — skill_group declaration pattern
@click.group("skill")
def skill_group() -> None:
    """Run registered skills."""

# cli.py lines 2601-2604 — subcommand on a group
@skill_group.command("run")
@click.argument("skill_id")
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
# ...

# cli.py lines 2710-2712 — agent_group as second example
@click.group("agent")
def agent_group() -> None:
    """Run registered subagents."""
```
F5 adaptation: create `hooks_group` with `@click.group("hooks")`, then
`@hooks_group.command("install")` and `@hooks_group.command("uninstall")`.

**Auth option pattern** (copy from `voss/harness/cli.py` lines 1300–1308):
```python
# cli.py lines 1302-1308 — AUTH_CHOICES option on do_cmd
@click.option(
    "--auth",
    "auth_pref",
    type=click.Choice(AUTH_CHOICES),
    default="auto",
    help="Credential source.",
)
```
F5 adaptation: apply the same `--auth` option to `consensus_cmd`. `AUTH_CHOICES` is
already defined at line 177 of `cli.py` and re-used across `do_cmd`, `chat_cmd`, etc.

**Provider resolution pattern** (copy from `voss/harness/cli.py` lines 1333–1334):
```python
# cli.py lines 1333-1334 — resolve auth then get config
res, provider = _resolve_auth_or_die(auth_pref)
cfg = get_config()
```
F5 adaptation: identical — call `_resolve_auth_or_die(auth_pref)` to get `provider`,
then `get_config()` to get `cfg.default_model`.

**AGENT_COMMANDS registration pattern** (copy from `voss/harness/cli.py` lines 3163–3188):
```python
# cli.py lines 3163-3188 — tuple of commands and groups
AGENT_COMMANDS = (
    do_cmd,
    # ... other commands ...
    skills_cmd,
    skill_group,
    agents_cmd,
    agent_group,
    memory_group,
    # ...
)
```
F5 adaptation: append `consensus_cmd` (standalone command) and `hooks_group` (group)
to this tuple. Pattern: flat command added as `consensus_cmd`, group added as `hooks_group`.

---

### `tests/harness/test_consensus.py` (test, request-response)

**Primary analog:** `tests/harness/test_cli.py` lines 1–19, 46–86
**Secondary analog:** `tests/harness/test_provider_response.py` lines 45–70 (async monkeypatch)

**Test file imports pattern** (copy from `tests/harness/test_cli.py` lines 1–7):
```python
from pathlib import Path

import pytest
from click.testing import CliRunner

from voss.harness.cli import main
```
F5 adaptation: also import `consensus_cmd` and `hooks_group` directly for isolated tests.

**CliRunner invocation pattern** (copy from `tests/harness/test_cli.py` lines 15–18, 47–50):
```python
# test_cli.py lines 15-18 — invoke with --help to verify registration
r = CliRunner().invoke(voss_main, ["--help"])
assert r.exit_code == 0
for verb in ("do", "chat", "doctor"):
    assert verb in r.output, f"missing agent verb: {verb}"

# test_cli.py lines 74-79 — invoke with options, assert exit code
r = CliRunner().invoke(main, ["do", "--auth", "none", "anything"])
assert r.exit_code == 2
assert "no usable credentials" in r.output
```
F5 adaptation: `CliRunner().invoke(main, ["consensus", "--staged"])` with monkeypatched
provider. `CliRunner().invoke(main, ["hooks", "install"])` with tmp_path.

**Async provider mock pattern** (copy from `tests/harness/test_provider_response.py` lines 45–68):
```python
# test_provider_response.py lines 62-67 — async fake for provider calls
async def fake_acompletion(**_kwargs):
    return response

monkeypatch.setattr("litellm.acompletion", fake_acompletion)
```
F5 adaptation: monkeypatch `voss.harness.consensus.run_critique` or mock
`provider.complete` to return a `SimpleNamespace(parsed=CritiqueResponse(...))`.
Since `consensus_cmd` calls `_resolve_auth_or_die`, tests should also monkeypatch
`voss.harness.cli._resolve_auth_or_die` to return a mock provider.

**Tmp_path filesystem pattern** (used throughout `test_edit_cmd.py` lines 23–77):
```python
# test_edit_cmd.py lines 23-26
def test_in_scope_write_does_not_prompt_expand(self, tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n")
```
F5 adaptation: `(tmp_path / ".git" / "hooks").mkdir(parents=True)` to set up a fake
git repo for hooks install tests. Use `tmp_path / ".voss" / "constraints.yml"` for
constraint file tests.

---

## Shared Patterns

### Provider Auth Resolution
**Source:** `voss/harness/cli.py` lines 177, 401–429
**Apply to:** `consensus_cmd` in `cli.py`
```python
# cli.py line 177
AUTH_CHOICES = ("auto", "claude", "codex", "api", "none")

# cli.py line 401 — call signature
def _resolve_auth_or_die(preference: str) -> tuple[auth_mod.Resolution, ModelProvider]:
```
Every harness command with LLM access calls `_resolve_auth_or_die(auth_pref)` before any
provider interaction. `consensus_cmd` follows this exactly.

### Fail-Open Exception Handling
**Source:** `voss/harness/agent.py` lines 1426–1437 (`_record_run_call`)
**Apply to:** `voss/harness/consensus.py` — the single-shot LLM call
```python
# agent.py lines 1426-1437
except Exception:  # noqa: BLE001 — sentinel-return is the contract
    telemetry.emit(...)
    return None
```
F5 does not use telemetry here but mirrors the `except Exception` + `# noqa: BLE001`
pattern. Difference: instead of returning `None`, F5 prints a warning on stderr and
calls `sys.exit(0)` (fail-open per D-16).

### YAML safe_load
**Source:** `voss/harness/code/config.py` line 46
**Apply to:** `voss/harness/consensus.py` — constraints.yml loading
```python
raw = yaml.safe_load(defaults_path.read_text(encoding="utf-8")) or {}
```
Always `safe_load`, never `yaml.load`. The `or {}` guard handles empty files gracefully.

### Click `--cwd` option
**Source:** `voss/harness/cli.py` line 2604 (skill_run_cmd), repeated across multiple commands
**Apply to:** `consensus_cmd` and `hooks_group` subcommands
```python
@click.option("--cwd", "cwd_str", default=".", type=click.Path(file_okay=False))
```
All harness commands that access the filesystem accept `--cwd` with `file_okay=False`.

### Pydantic `extra="ignore"` on LLM response models
**Source:** `voss/harness/agent.py` lines 199–203 (`RunSemantics`)
**Apply to:** `CritiqueResponse`, `Violation`, `CritiqueSummary` in `consensus.py`
```python
# agent.py lines 199-203
model_config = {"extra": "ignore"}
```
LLM responses hallucinate fields. `extra="ignore"` prevents `ValidationError` on unknown
keys, which would otherwise cause a fail-open fallback when the response is actually valid.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `.git/hooks/pre-commit` (written by `hooks install`) | config | file-I/O | No existing hook-write pattern in codebase; it is a 3-line shell file write — use `Path.write_text(HOOK_SHIM)` with `chmod 0o755` |

---

## Metadata

**Analog search scope:** `voss/harness/`, `tests/harness/`
**Files scanned:** 8 analog files read, 3 grep searches
**Pattern extraction date:** 2026-05-22
