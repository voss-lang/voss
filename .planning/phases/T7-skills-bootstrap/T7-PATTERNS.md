# Phase T7: Skills Bootstrap - Pattern Map

**Mapped:** 2026-05-17
**Files analyzed:** 16 new/modified files
**Analogs found:** 15 / 16 (1 file type has no prior example in the codebase)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `voss/harness/skill_registry.py` | registry (modify) | CRUD | itself (`default_skill_registry()` analyze block) | exact |
| `voss/harness/skills/rename_symbol.py` | skill handler | request-response (deterministic) | `voss/harness/skills/analyze.py` | role-match (sync, no run_turn) |
| `voss/harness/skills/add_test.py` | skill handler | request-response (agentic) | `voss/harness/skills/analyze.py` | exact |
| `voss/harness/skills/summarize_diff.py` | skill handler | request-response (agentic) | `voss/harness/skills/analyze.py` | exact |
| `voss/harness/skills/port_py_to_voss.py` | skill handler | request-response (agentic) | `voss/harness/skills/analyze.py` | exact |
| `voss/harness/skills/audit_cognition.py` | skill handler | request-response (agentic) | `voss/harness/skills/analyze.py` | exact |
| `voss/harness/skills/voss_lint_as_skill.py` | skill handler | request-response (deterministic) | `voss/harness/skills/analyze.py` | role-match (sync, no run_turn) |
| `voss/harness/skills/voss/add-test.voss` | companion artifact | — | `samples/classify.voss` | role-match |
| `voss/harness/skills/voss/summarize-diff.voss` | companion artifact | — | `samples/classify.voss` | role-match |
| `voss/harness/skills/voss/port-py-to-voss.voss` | companion artifact | — | `samples/research.voss` | role-match |
| `voss/harness/skills/voss/audit-cognition.voss` | companion artifact | — | `samples/classify.voss` | role-match |
| `tests/skills/__init__.py` | test package marker | — | `tests/harness/__init__.py` | exact |
| `tests/skills/conftest.py` | test fixtures | — | `tests/harness/conftest.py` | exact |
| `tests/skills/test_skills_smoke.py` | test suite | request-response | `tests/harness/test_agent_integration.py` | role-match |
| `tests/skills/fixtures/<skill>/` (6 dirs) | test seed data | — | (no analog — new pattern) | none |
| `.github/workflows/ci.yml` | CI config (modify) | — | itself (lines 46-48, existing `voss check` steps) | exact |

---

## Pattern Assignments

### `voss/harness/skill_registry.py` (registry, modify)

**Analog:** `voss/harness/skill_registry.py` itself — add 6 new `SkillEntry` blocks mirroring the existing `analyze` block.

**Existing registration pattern** (lines 38-58):
```python
def default_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()

    def analyze(ctx: Any, _args: list[str]) -> None:
        from .cli import _handle_analyze

        _handle_analyze(
            cwd=ctx.cwd,
            provider=ctx.provider,
            history=ctx.history,
            record=ctx.record,
            renderer=ctx.renderer,
            tools=ctx.tools,
            gate=ctx.gate,
        )

    registry.register(
        SkillEntry(
            id="analyze",
            description="Refresh project cognition (.voss/ + .voss-cache/).",
            handler=analyze,
            mutating=True,
        )
    )
    return registry
```

**Pattern to copy for each new skill** — substitute underscored import name, hyphenated id, description, mutating flag:
```python
    def rename_symbol(ctx: Any, args: list[str]) -> None:
        from .skills.rename_symbol import run

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

    registry.register(
        SkillEntry(
            id="rename-symbol",
            description="Anchor + scope-aware rename across the repo.",
            handler=rename_symbol,
            mutating=True,
        )
    )
```

**SkillEntry shape** (lines 10-15):
```python
@dataclass(frozen=True)
class SkillEntry:
    id: str           # hyphenated slug: "rename-symbol"
    description: str
    handler: SkillHandler  # (ctx: Any, args: list[str]) -> None
    mutating: bool = False
```

**Critical:** Module filenames are underscored (`rename_symbol.py`); `SkillEntry.id` is hyphenated (`"rename-symbol"`). The `analyze` registration passes `_args` (ignored); new skills pass `args` (used by deterministic skills for positional parameters). The `args` kwarg must be added to the `run()` signature for deterministic skills.

**All 6 registrations summary:**

| `SkillEntry.id` | import module | `mutating` |
|----------------|--------------|-----------|
| `"rename-symbol"` | `rename_symbol` | `True` |
| `"add-test"` | `add_test` | `True` |
| `"summarize-diff"` | `summarize_diff` | `False` |
| `"port-py-to-voss"` | `port_py_to_voss` | `True` |
| `"audit-cognition"` | `audit_cognition` | `False` |
| `"voss-lint-as-skill"` | `voss_lint_as_skill` | `False` |

---

### `voss/harness/skills/add_test.py` (agentic skill handler)
### `voss/harness/skills/summarize_diff.py` (agentic skill handler)
### `voss/harness/skills/port_py_to_voss.py` (agentic skill handler)
### `voss/harness/skills/audit_cognition.py` (agentic skill handler)

**Analog:** `voss/harness/skills/analyze.py` — copy the module structure exactly.

**Imports pattern** (lines 10-19):
```python
from __future__ import annotations

import asyncio
from pathlib import Path

import click

from .. import cognition, voss_md   # only if needed; audit_cognition uses cognition
from ..agent import run_turn
```

**Minimal agentic skill `run()` function** (lines 25-68, distilled):
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
) -> None:
    prompt = (
        "Summarize the current git diff as a pull request description. "
        "Output ONLY structured markdown with sections ## Title, ## Summary, and ## Changes."
    )
    asyncio.run(
        run_turn(
            prompt,
            tools=tools,
            cwd=cwd,
            renderer=renderer,
            model=record.model,
            provider=provider,
            history=history,
            permissions=gate,
            cognition=None,
            session_id=record.id,
        )
    )
```

**`run_turn()` full signature** (confirmed `voss/harness/agent.py:412-428`):
```python
async def run_turn(
    task: str,
    *,
    tools: dict[str, ToolEntry],
    cwd: Path,
    renderer: Renderer,
    confidence_threshold: float = 0.60,
    token_budget: int = 60_000,
    model: str | None = None,
    provider: ModelProvider | None = None,
    history: EpisodicMemory | None = None,
    permissions: PermissionGate | None = None,
    session_id: str | None = None,
    cognition=None,
    prior_context: dict | None = None,
    voss_md_text: str | None = None,
) -> TurnResult:
```

**Per-skill prompt notes:**

- `summarize_diff.py`: prompt instructs agent to call `git_diff` and produce `## Title`, `## Summary`, `## Changes` sections. No file writes.
- `add_test.py`: prompt instructs agent to find a public function and write a pytest test via `fs_write`. Target `tests/test_<module>.py`.
- `port_py_to_voss.py`: prompt instructs agent to translate a Python file to `.voss` using classify/support/research sample shapes as guides and write via `fs_write`. `args[0]` = source Python file path.
- `audit_cognition.py`: load cognition bundle first (pure Python, before `asyncio.run`), compute drift, build prompt including drift reason, call `run_turn`. Prompt MUST include "Do NOT write to any file. Output your proposal as a paragraph starting with 'PROPOSAL:'." See cognition pattern below.

**`audit_cognition.py` pre-`run_turn` preamble** (uses `cognition.*` APIs from `voss/harness/cognition.py:63,253,278`):
```python
from .. import cognition

def run(*, cwd, provider, history, record, renderer, tools, gate) -> None:
    bundle = cognition.load(cwd)
    if not bundle.initialized:
        click.echo("cognition not initialized — run /analyze first", err=True)
        return
    if bundle.architecture_frontmatter is None:
        click.echo("no architecture frontmatter — run /analyze first", err=True)
        return

    drift: cognition.DriftStatus = cognition.drift_check(cwd, bundle.architecture_frontmatter)
    prompt = (
        f"The project cognition is {'stale' if drift.is_stale else 'current'}. "
        f"Drift reason: {drift.reason or 'none'}. "
        "Propose a one-paragraph update to the architecture description. "
        "Do NOT write to any file. Output your proposal as a paragraph starting with 'PROPOSAL:'."
    )
    asyncio.run(run_turn(prompt, tools=tools, cwd=cwd, renderer=renderer,
                          model=record.model, provider=provider, history=history,
                          permissions=gate, cognition=None, session_id=record.id))
```

**`DriftStatus` dataclass** (confirmed `voss/harness/cognition.py:253`):
```python
@dataclass
class DriftStatus:
    is_stale: bool
    head_diverged_by: int
    file_count_delta: int
    days_elapsed: int
    reason: str = ""
```

---

### `voss/harness/skills/rename_symbol.py` (deterministic, mutating)

**Analog:** `voss/harness/skills/analyze.py` for module shape; deterministic tools-only path (no `run_turn`).

**Imports pattern:**
```python
from __future__ import annotations

import asyncio
from pathlib import Path

import click

from ..permissions import PermissionGate
```

**Core pattern — deterministic gate-checked tool calls:**
```python
def run(
    *,
    cwd: Path,
    provider,   # unused — deterministic skill
    history,    # unused
    record,     # unused
    renderer,
    tools,
    gate,
    args=None,
) -> None:
    if not args or len(args) < 2:
        click.echo("usage: rename-symbol <old> <new>", err=True)
        return
    old, new = args[0], args[1]

    # 1. Find all occurrences via gated read tool (no gate.check needed — fs_grep is read-only)
    hits_raw = asyncio.run(tools["fs_grep"].invoke(pattern=rf"\b{old}\b", glob="**/*.py"))
    # 2. Parse hits_raw into list of (file_path, context_line)
    # 3. For each file, explicitly call gate.check() before mutating
    allowed, reason = gate.check("fs_edit", {"path": str(path), "old": old, "new": new},
                                  is_mutating=True)
    if not allowed:
        click.echo(f"rename-symbol: {reason}", err=True)
        return
    asyncio.run(tools["fs_edit"].invoke(path=str(path), old=context_old, new=context_new))
```

**Critical landmine:** `ToolEntry.invoke(**kwargs)` bypasses the permission gate. For deterministic skills operating outside `run_turn`, call `gate.check(tool_name, args_dict, is_mutating=True)` explicitly before each `fs_edit`/`fs_write` invocation. Return early if `allowed=False`.

**Tool signatures** (confirmed `voss/harness/tools.py`):
```python
# Read-only — no gate.check() needed before invoke
tools["fs_grep"].invoke(pattern: str, glob: str = "**/*")
tools["fs_glob"].invoke(pattern: str)
tools["fs_read"].invoke(path: str)

# Mutating — call gate.check() first
tools["fs_edit"].invoke(path: str, old: str, new: str)
tools["fs_write"].invoke(path: str, content: str)

# For agentic skills (via run_turn):
tools["git_diff"].invoke(staged: bool = False, path: str = "")
```

---

### `voss/harness/skills/voss_lint_as_skill.py` (deterministic, read-only)

**Analog:** `voss/harness/skills/analyze.py` for module shape; direct Python API path instead of `run_turn`.

**Imports pattern:**
```python
from __future__ import annotations

import json
from pathlib import Path

import click

from voss.parser import parse          # public: voss/parser.py:791
from voss.analyzer import analyze      # public: voss/analyzer.py:755
from voss.diagnostics import Diagnostic, AnalysisResult
```

**`parse()` public signature** (confirmed `voss/parser.py:791`):
```python
def parse(source: str, file: str = "<string>") -> Program:
```

**`Diagnostic` and `Span` fields** (confirmed `voss/diagnostics.py:12-18`):
```python
@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: DiagnosticSeverity  # "warning" | "error"
    code: str                     # rule ID, e.g. "E001"
    message: str
    span: Span
    hint: str | None = None

# Span fields used in schema:
span.file          # str — source file path
span.line_start    # int
span.col_start     # int
```

**Frozen JSON schema (M11 contract):**
```json
{
  "version": 1,
  "findings": [
    {
      "file": "foo.voss",
      "line": 12,
      "col": 3,
      "rule": "E001",
      "severity": "error",
      "msg": "undefined variable: bar",
      "hint": null
    }
  ]
}
```

**Core pattern:**
```python
def run(
    *,
    cwd: Path,
    provider,   # unused
    history,    # unused
    record,     # unused
    renderer,
    tools,
    gate,
    args=None,
) -> None:
    target = Path(args[0]) if args else cwd
    if not target.is_absolute():
        target = cwd / target

    all_diags: list[Diagnostic] = []
    for voss_file in sorted(target.rglob("*.voss")):
        try:
            source = voss_file.read_text()
            program = parse(source, file=str(voss_file))
            result = analyze(program, source_path=str(voss_file), emit_indexes=False)
            all_diags.extend(result.diagnostics)
        except Exception as exc:
            # surface parse errors as error findings
            ...

    schema = {
        "version": 1,
        "findings": [
            {
                "file": d.span.file,
                "line": d.span.line_start,
                "col": d.span.col_start,
                "rule": d.code,
                "severity": d.severity,
                "msg": d.message,
                "hint": d.hint,
            }
            for d in all_diags
        ],
    }
    click.echo(json.dumps(schema, indent=2))
```

**Landmine:** Do NOT import `_parse_file` or `_walk_voss_sources` from `voss/cli.py` — private helpers. Use `path.rglob("*.voss")` inline and `voss.parser.parse()` directly.

---

### `.voss` Companion Artifacts

**Analog:** `samples/classify.voss` (simple fn + `probable<T>` + confidence gate) for `add-test.voss`, `summarize-diff.voss`, `audit-cognition.voss`; `samples/research.voss` (agent + try/catch + ctx budget) for `port-py-to-voss.voss`.

#### `voss/harness/skills/voss/add-test.voss`

**Pattern from** `samples/classify.voss` (lines 1-14):
```voss
# classify.voss — probable<T>, confidence gate (@ p >= 0.80)
fn classifyIntent(input: string) -> string {
    let intent: probable<string> = ask("Classify the intent: " + input)

    if intent @ p >= 0.80 {
        return intent.value
    } else {
        return "unknown"
    }
}
```

**Target shape:**
```voss
# add-test.voss — companion for SKL-02; demonstrates fn + probable<T> + confidence gate
fn findPublicFn(path: string) -> string {
    let fn_name: probable<string> = ask("Find the main public function in file: " + path)

    if fn_name @ p >= 0.80 {
        return fn_name.value
    } else {
        return "unknown"
    }
}

let result = findPublicFn("target.py")
print(result)
```

#### `voss/harness/skills/voss/summarize-diff.voss`

**Target shape** (simple fn + ctx budget — from `loop.voss:13-23` pattern):
```voss
# summarize-diff.voss — companion for SKL-03; demonstrates fn + ctx(budget) + yield ask
fn summarizeDiff(diff: string) -> string {
    ctx(budget: 3000 tokens) {
        yield ask("Summarize this git diff as a PR description with ## Title, ## Summary, ## Changes sections:\n" + diff)
    }
}
```

#### `voss/harness/skills/voss/port-py-to-voss.voss`

**Pattern from** `samples/research.voss` (lines 6-19) — agent + ctx + try/catch:
```voss
agent Researcher(topic: string) -> string {
    system: "You are a research analyst."
    tools: [webSearch]
    ctx(budget: 2000 tokens) {
        try {
            let results = webSearch(topic, max_results: 5)
            include results
        } catch e {
            include "web search unavailable"
        }
        yield ask("Summarize findings on: " + topic)
    }
}
```

**Target shape:**
```voss
# port-py-to-voss.voss — companion for SKL-04; demonstrates fn + ctx + try/catch
fn translatePython(pySource: string) -> string {
    ctx(budget: 6000 tokens) {
        try {
            include pySource
            yield ask("Translate this Python file to .voss syntax using the classify/support/research sample shapes as guides.")
        } catch e {
            return "translation failed: " + e
        }
    }
}
```

#### `voss/harness/skills/voss/audit-cognition.voss`

**Target shape** (simple fn + ctx budget):
```voss
# audit-cognition.voss — companion for SKL-05; demonstrates fn + ctx(budget) + yield ask
fn proposeCognitionUpdate(drift: string) -> string {
    ctx(budget: 2000 tokens) {
        yield ask("Given this drift status: " + drift + " — propose a one-paragraph architecture.md update. Do NOT write any file.")
    }
}
```

**Validation requirement:** All 4 `.voss` companions must pass `python -m voss.cli check voss/harness/skills/voss/` locally before commit. Use the simplest construct that compiles — if a shape fails `voss check`, fall back to `fn` + `ctx(budget)` + `yield ask()`.

---

### `tests/skills/conftest.py` (test fixtures)

**Analog:** `tests/harness/conftest.py` — copy `isolated_state` and `git_repo` fixtures verbatim; add `FakeProvider` class.

**`isolated_state` autouse fixture** (lines 28-31):
```python
@pytest.fixture(autouse=True)
def isolated_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    return tmp_path
```

**`git_repo` fixture** (lines 34-42):
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

**`FakeProvider` class** — copy from `tests/harness/test_agent_integration.py:30-102`:
```python
from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage
from voss.harness.agent import Plan, ToolCall

class FakeProvider:
    def __init__(self, plan: Plan, cost: float = 0.001):
        self.plan = plan
        self.cost = cost
        self.calls: list[dict] = []
        self._stream_index = 0

    async def complete(self, *, messages, model, response_format=None,
                       tools=None, temperature=1.0, max_tokens=None, timeout=None):
        self.calls.append({"model": model, "messages": messages, "schema": response_format})
        from voss_runtime.providers.base import ProviderResponse
        return ProviderResponse(
            text=self.plan.model_dump_json(), model=model,
            prompt_tokens=50, completion_tokens=50, cost_usd=self.cost,
            raw={"fake": True},
            parsed=self.plan if response_format is Plan else None,
        )

    def stream(self, **kwargs):
        self.calls.append({"model": kwargs.get("model"),
                           "messages": kwargs.get("messages"),
                           "schema": kwargs.get("response_format")})
        idx = self._stream_index
        self._stream_index += 1
        if idx == 0:
            plan_to_emit = self.plan
        else:
            plan_to_emit = Plan(
                rationale="(synthetic done plan from FakeProvider)",
                steps=[],
                confidence=self.plan.confidence,
                final_when_done=self.plan.final_when_done or "(stub final)",
            )

        async def _gen():
            yield TextDelta(text="…")
            yield ParsedPlan(plan=plan_to_emit)
            yield Usage(prompt_tokens=50, completion_tokens=50, cost_usd=self.cost)
            yield Done(stop_reason="end_turn")

        return _gen()

    def count_tokens(self, *, text: str, model: str) -> int:
        return max(len(text) // 4, 1)
```

**Critical (Pitfall 4):** `run_turn` calls `provider.stream()`, NOT `provider.complete()`. FakeProvider without `stream()` raises `AttributeError` at test time. Always copy the full shape.

---

### `tests/skills/test_skills_smoke.py` (test suite)

**Analog:** `tests/harness/test_agent_integration.py` for `FakeProvider`/`run_turn` test structure; `PermissionGate(auto_yes=True)` + `PlainRenderer()` pattern.

**Imports pattern** (from `tests/harness/test_agent_integration.py:15-19`):
```python
from voss.harness.agent import Plan, ToolCall, run_turn
from voss.harness.permissions import PermissionGate
from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage
from voss.harness.render import PlainRenderer
from voss.harness.tools import make_toolset
```

**Test gate + renderer pattern** (from `tests/harness/test_agent_integration.py:215-217`):
```python
provider = FakeProvider(plan)
result = asyncio.run(run_turn(
    "task description",
    tools=make_toolset(project),
    cwd=project,
    renderer=PlainRenderer(),
    provider=provider,
    permissions=PermissionGate(auto_yes=True),
))
```

**Agentic skill test pattern** — invoke the skill `run()` directly with stub objects:
```python
def test_summarize_diff(git_repo: Path) -> None:
    plan = Plan(
        rationale="summarize diff",
        steps=[ToolCall(name="git_diff", args={})],
        confidence=0.90,
        final_when_done="## Title\nfoo\n## Summary\nbar\n## Changes\nbaz",
    )
    provider = FakeProvider(plan)

    from voss.harness.skills.summarize_diff import run
    from voss.harness.session import SessionRecord  # for record stub
    import types

    record = types.SimpleNamespace(model="fake-model", id="test-session")
    run(
        cwd=git_repo,
        provider=provider,
        history=None,
        record=record,
        renderer=PlainRenderer(),
        tools=make_toolset(git_repo),
        gate=PermissionGate(auto_yes=True),
    )
    # assert output captured via capsys or check provider.calls
```

**Deterministic skill test pattern** (SKL-01, SKL-06 — invoke `run()` directly, no FakeProvider):
```python
def test_voss_lint(tmp_path: Path) -> None:
    bad_voss = tmp_path / "bad.voss"
    bad_voss.write_text("fn broken(x: int) {\n    let y = undefined_var\n}\n")

    from voss.harness.skills.voss_lint_as_skill import run
    import types, json
    record = types.SimpleNamespace(model="fake", id="test")
    # capture stdout
    import io
    from unittest.mock import patch
    buf = io.StringIO()
    with patch("click.echo", side_effect=lambda s, **kw: buf.write(str(s) + "\n")):
        run(cwd=tmp_path, provider=None, history=None, record=record,
            renderer=PlainRenderer(), tools=make_toolset(tmp_path),
            gate=PermissionGate(auto_yes=True), args=[str(tmp_path)])
    output = buf.getvalue()
    schema = json.loads(output)
    assert schema["version"] == 1
    assert isinstance(schema["findings"], list)
```

**Registry count smoke test** (Pitfall 6 guard):
```python
def test_registry_count() -> None:
    from voss.harness.skill_registry import default_skill_registry
    registry = default_skill_registry()
    assert len(registry.ids()) == 7  # analyze + 6 new
```

---

### `.github/workflows/ci.yml` (CI config, modify)

**Analog:** The file itself at lines 46-48 — existing `voss check` step pattern.

**Existing pattern** (lines 46-48):
```yaml
      - name: voss check harness sources (M4 DOG-06)
        run: python -m voss.cli check voss/harness/agent/
      - run: python -m voss.cli check voss-demos/
```

**New step to add** (insert after line 48, before the grep gate step):
```yaml
      - name: voss check skills voss companions (T7)
        run: python -m voss.cli check voss/harness/skills/voss/
```

**Placement:** Inside the `stub` job (line 32), after the existing `voss check` steps, before the `pytest` run. The `pip install -e ".[dev]"` step at line 45 already makes `voss check` available.

---

## Shared Patterns

### Permission Gate Check (deterministic skills only)

**Source:** `voss/harness/permissions.py:169-194`
**Apply to:** `rename_symbol.py` and any other deterministic skill that calls mutating tools directly

```python
# BEFORE every mutating tool invoke() in deterministic skills:
allowed, reason = gate.check(
    "fs_edit",
    {"path": str(path), "old": old_text, "new": new_text},
    is_mutating=True,
)
if not allowed:
    click.echo(f"skill-name: {reason}", err=True)
    return
asyncio.run(tools["fs_edit"].invoke(path=str(path), old=old_text, new=new_text))
```

**Mode behavior** (`voss/harness/permissions.py:49-64`):
- `plan` mode: `is_mutating=True` → denied (`"denied by mode plan"`)
- `edit` mode: `fs_edit`/`fs_write` → allowed; `shell_run` → denied
- `auto` mode: everything allowed

### `asyncio.run()` Wrapper for Skill `run()` Functions

**Source:** `voss/harness/skills/analyze.py:55-68`
**Apply to:** All 4 agentic skill handlers

```python
asyncio.run(
    run_turn(
        prompt,
        tools=tools,
        cwd=cwd,
        renderer=renderer,
        model=record.model,
        provider=provider,
        history=history,
        permissions=gate,
        cognition=None,
        session_id=record.id,
    )
)
```

`run()` is a sync function (SkillHandler contract). Wrap `run_turn()` in `asyncio.run()` — never add `async` to `run()`.

### `click.echo()` for Output

**Source:** `voss/harness/skills/analyze.py:84-93`
**Apply to:** All deterministic skill handlers for user-visible messages

```python
import click
click.echo("some message", err=True)   # warnings/errors to stderr
click.echo(json.dumps(schema, indent=2))  # structured output to stdout (SKL-06)
```

Agentic skills output via `renderer` (through `run_turn`); deterministic skills use `click.echo()` directly.

### Isolated State + Git Repo Fixtures

**Source:** `tests/harness/conftest.py:28-42`
**Apply to:** `tests/skills/conftest.py`

Copy `isolated_state` (autouse — XDG sandbox per test) and `git_repo` (opt-in — real git tree) verbatim. The `tests/skills/conftest.py` should also define `FakeProvider` as a module-level class (not a fixture) so tests can construct it inline with different plans.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `tests/skills/fixtures/<skill>/` seed repos | test data | — | No existing skill test fixtures in the codebase (`find tests -name "*skill*"` returns 0). The shape (seed files in a named directory) is borrowed conceptually from M5's `task.toml` + `fixture/` pattern but M5 is not shipped; executor should create these as plain directories with static Python/`.voss` seed files. |

---

## Metadata

**Analog search scope:** `voss/harness/skills/`, `voss/harness/`, `tests/harness/`, `samples/`, `voss/harness/agent/`, `voss/diagnostics.py`, `voss/parser.py`, `.github/workflows/`
**Files read:** 14 source files
**Pattern extraction date:** 2026-05-17
