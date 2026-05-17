# Phase T7: Skills Bootstrap - Research

**Researched:** 2026-05-17
**Domain:** Skill registry integration, Python skill handlers, `.voss` companion artifacts, hermetic test fixtures
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Eval / verification strategy**
- D-01: Standalone `tests/skills/` suite — `tests/skills/fixtures/<skill>/` (seed repo + expected artifacts) and `tests/skills/test_skills_smoke.py`. Decoupled from M5's golden suite.
- D-02: Verification is deterministic + hermetic — no LLM-as-judge. Per-skill post-conditions: exit 0, no permission escalation, and:
  - `rename-symbol` → `git diff` == expected patch
  - `add-test` → `pytest --collect-only` finds the new test
  - `summarize-diff` → output non-empty + has PR-ish sections
  - `voss-lint` → emitted JSON validates against the frozen schema + contains known seeded findings
  - `port-py-to-voss` → `voss check` exits 0 on the generated `.voss`
  - `audit-cognition` → a proposal block is emitted, no write to `architecture.md`
- D-03: Agentic skills run under a stub provider in tests.

**Authoring substrate**
- D-04: All 6 runtime handlers are Python modules `voss/harness/skills/<id>.py`, following `analyze.py`'s `run(*, cwd, provider, history, record, renderer, tools, gate)` pattern.
- D-05: 4 agentic skills also ship a companion `.voss` at `voss/harness/skills/voss/<id>.voss` that `voss check` must pass in CI.
- D-06: 2 deterministic skills (`rename-symbol`, `voss-lint-as-skill`) are Python-only, no `.voss` companion.

**Deterministic vs agentic split**
- D-07: Agentic (invokes `run_turn`): `summarize-diff`, `add-test`, `port-py-to-voss`, `audit-cognition`.
- D-08: Deterministic (no provider call): `rename-symbol`, `voss-lint-as-skill`.

**Mutating classification + permission posture**
- D-09: `mutating: true` → `rename-symbol`, `add-test`, `port-py-to-voss`. Write through `fs_edit`/`fs_write`; no skill-level permission escalation.
- D-10: `mutating: false` → `summarize-diff`, `voss-lint-as-skill`, `audit-cognition`. `audit-cognition` never writes `architecture.md`.
- D-11: Skills never bypass the central tool permission layer.

**Output contract**
- D-12: Per-skill output:
  - `voss-lint-as-skill` → stable JSON schema `{version, findings:[{file,line,rule,severity,msg}]}` — the M11 contract.
  - `summarize-diff` → structured markdown with `## Title`, `## Summary`, `## Changes`.
  - `rename-symbol`, `add-test`, `port-py-to-voss` → human-readable text; the meaningful effect is file mutation.
  - `audit-cognition` → human-readable proposal block (no write).
- D-13: No uniform JSON envelope across all skills.

### Claude's Discretion

- Symbol-scoping engine for `rename-symbol` (AST vs anchor+grep heuristic) — researcher/planner choose.
- Test-framework detection for `add-test` (pytest assumed; planner confirms).
- Exact `.voss` companion shapes for the 4 agentic skills (must `voss check`-pass).
- Which `voss check` diagnostic fields map into SKL-06's frozen JSON schema.
- Drift-detection mechanism reuse for `audit-cognition` (reuse `cognition.*` drift APIs from M2).

### Deferred Ideas (OUT OF SCOPE)

- `.voss`-skill execution path / loader.
- Hard 1:1 M5 golden-suite pairing + LLM-judge skill scoring.
- M11 (lint-as-skill consumer) and M15 (marketplace).
- Uniform cross-skill JSON output envelope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SKL-01 | `rename-symbol` — anchor + scope-aware rename across repo (deterministic, mutating) | `fs_grep`/`fs_edit` toolset confirmed; Python stdlib `ast` importable but NOT used in codebase; recommend heuristic approach using existing tools |
| SKL-02 | `add-test` — locate a public function, generate a unit test, plant a failing assertion (agentic, mutating) | `FakeProvider`/`run_turn` pattern confirmed; pytest confirmed as project test framework |
| SKL-03 | `summarize-diff` — `git diff` → structured markdown PR description (agentic, read-only) | `git_diff` tool available in toolset; `run_turn` path confirmed |
| SKL-04 | `port-py-to-voss` — Python → `.voss` for classify/support/research sample shapes (agentic, mutating) | Sample shapes in `samples/*.voss` confirmed; `fs_write` gated tool for output |
| SKL-05 | `audit-cognition` — re-run analyze against drift; emit proposal block, never writes (agentic, read-only) | `cognition.load()`, `cognition.drift_check()`, `cognition.build_bootstrap_inventory()` all confirmed; `DriftStatus` dataclass available |
| SKL-06 | `voss-lint-as-skill` — wraps `voss check` with frozen JSON diagnostics schema; M11 contract (deterministic, read-only) | `Diagnostic` fields confirmed: `severity`, `code`, `message`, `span.file`, `span.line_start`, `span.col_start`; `hint` optional; `voss.analyzer.analyze()` importable directly |
</phase_requirements>

---

## Summary

Phase T7 adds 6 skill entries to the `default_skill_registry()` in `voss/harness/skill_registry.py`, one Python handler module per skill under `voss/harness/skills/<id>.py`, companion `.voss` artifacts for the 4 agentic skills at `voss/harness/skills/voss/<id>.voss`, and a standalone hermetic test suite at `tests/skills/`. The single integration point is `default_skill_registry()` — adding `SkillEntry` objects there is sufficient for `/skill`, `/skills`, `voss skill run`, and `voss skills` discoverability. No other wiring is needed.

The skill registry, CLI surface, and permission gate are fully operational and LOCKED. The research confirms every locked decision in CONTEXT.md is grounded in the existing code. The `analyze.py` handler is a copy template for all 4 agentic skills. The `FakeProvider`/`PlainRenderer`/`PermissionGate(auto_yes=True)` test triad is established across multiple existing test suites and slots directly into the `tests/skills/` hermetic design. The `voss check` Python API (`voss.analyzer.analyze()` + `voss.diagnostics.Diagnostic`) is importable from within harness code, enabling SKL-06 to avoid subprocess parsing.

**Primary recommendation:** Implement in 3 waves — Wave 0 (test scaffold + fixtures), Wave 1 (deterministic skills SKL-01 + SKL-06 + `.voss` companions for agentic stubs), Wave 2 (agentic skills SKL-02..SKL-05). All waves are independently verifiable. SKL-01 and SKL-06 can proceed in parallel with `.voss` companion authoring.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Skill registry entries | Harness (`voss/harness/skill_registry.py`) | — | `default_skill_registry()` is the single registration point; CLI reads from it |
| Python skill handlers | Harness (`voss/harness/skills/`) | — | Mirror `analyze.py` pattern; all 6 handlers live here |
| Permission enforcement | Harness (`voss/harness/permissions.py`) | PermissionGate | Skills never bypass — gate owns all mode-tier checks |
| `.voss` companion artifacts | Language layer (`voss/harness/skills/voss/`) | `voss check` (CI) | Dogfood demonstration; not exec path |
| Drift detection (SKL-05) | Harness (`voss/harness/cognition.py`) | — | `cognition.load()` + `drift_check()` already encapsulate all drift logic |
| Diagnostic schema (SKL-06) | Compiler (`voss/diagnostics.py`, `voss/analyzer.py`) | Harness skill handler | `Diagnostic` dataclass fields are the schema source of truth |
| Hermetic test fixtures | `tests/skills/fixtures/<skill>/` | pytest + `git_repo` fixture | Seed repo pattern from harness conftest; no live provider |
| CLI discoverability | `voss/harness/cli.py` `_print_skills` + `_skill` handlers | — | Already wired; registry entry addition is sufficient |

---

## Standard Stack

### Core (no new packages — all existing)

| Library / Module | Purpose | Source |
|-----------------|---------|--------|
| `voss.harness.skill_registry` | `SkillEntry`, `SkillRegistry`, `default_skill_registry()` | `voss/harness/skill_registry.py` |
| `voss.harness.agent` | `run_turn`, `Plan`, `ToolCall`, `TurnResult` | `voss/harness/agent.py` |
| `voss.harness.permissions` | `PermissionGate` (mode-tier enforcement) | `voss/harness/permissions.py` |
| `voss.harness.tools` | `make_toolset`, `ToolEntry`, `fs_edit`, `fs_write`, `fs_grep`, `fs_glob`, `fs_read`, `git_diff`, `voss_check` | `voss/harness/tools.py` |
| `voss.harness.cognition` | `load()`, `drift_check()`, `build_bootstrap_inventory()`, `bootstrap_prompt()`, `DriftStatus`, `CognitionBundle` | `voss/harness/cognition.py` |
| `voss.harness.render` | `PlainRenderer` (test path) | `voss/harness/render.py` |
| `voss.analyzer` | `analyze()` → `AnalysisResult` (direct Python API for SKL-06) | `voss/analyzer.py:755` |
| `voss.diagnostics` | `Diagnostic`, `AnalysisResult` | `voss/diagnostics.py` |
| `voss.parser` | `parse`/`_parse_file` (needed by SKL-06 Python API path) | `voss/cli.py` (internal) |
| `pytest` | Test framework (already in `[dev]` extras) | `pyproject.toml [tool.pytest.ini_options]` |
| `asyncio` | `asyncio.run()` to drive agentic skills synchronously | stdlib |

**No new packages required.** [VERIFIED: codebase grep]

### Supporting (test-only patterns from existing harness tests)

| Pattern | Purpose | Precedent Location |
|---------|---------|-------------------|
| `FakeProvider` class | Stub provider for agentic skill tests | `tests/harness/test_agent_integration.py:30`, `tests/harness/test_extensions.py:32`, `tests/harness/test_voss_loop_parity.py:19` |
| `PermissionGate(auto_yes=True)` | Non-interactive gate for hermetic tests | `tests/harness/test_agent_integration.py:216` |
| `PlainRenderer()` | Renderer with no TUI deps for tests | `tests/harness/test_agent_integration.py:15,215` |
| `git_repo` fixture | Creates temp git repo with initial commit | `tests/harness/conftest.py:35` |
| `isolated_state` autouse fixture | XDG_STATE_HOME sandbox per test | `tests/harness/conftest.py:29` |

---

## Package Legitimacy Audit

> No new packages are introduced in T7. All dependencies are existing project packages.

| Package | Registry | Status |
|---------|----------|--------|
| All stdlib + project packages | — | Existing; no new installs |

**No slopcheck needed — zero new package dependencies.**

---

## Architecture Patterns

### System Architecture Diagram

```
User invokes: `/skill rename-symbol foo bar`  OR  `voss skill run rename-symbol foo bar`
                            |
                    cli.py `_skill()` or `skill_run_cmd()`
                            |
                    ctx.skill_registry.get("rename-symbol")
                            |
                    entry.handler(ctx, ["foo", "bar"])
                            |
              voss/harness/skills/rename-symbol.py  run(*, cwd, provider, history, record, renderer, tools, gate)
              [deterministic path: no provider call]
                            |
                    fs_grep(pattern="\\bfoo\\b") → locate sites
                            |
                    [plan mode] → PermissionGate.check() → denied by mode plan
                    [edit/auto] → PermissionGate.check() → allowed → fs_edit(path, old, new) per site
                            |
                    renderer / click.echo → human-readable result
                            |
                    returns None  ← SkillHandler contract

User invokes: `/skill summarize-diff`
                            |
                    voss/harness/skills/summarize-diff.py run(...)
                            |
                    asyncio.run(run_turn(prompt, tools=tools, cwd=cwd, renderer=renderer,
                                        model=record.model, provider=provider,
                                        history=history, permissions=gate, ...))
                            |
                    [test path] FakeProvider.stream() → ParsedPlan → synthetic Done plan
                    [live path] provider.stream() → real LLM plan with git_diff tool call
                            |
                    git_diff tool → git diff output
                            |
                    Plan.final_when_done → structured markdown output via renderer
                            |
                    returns None
```

### Recommended Project Structure

```
voss/harness/skills/
├── __init__.py              # (exists, empty)
├── analyze.py               # (existing — copy template)
├── rename-symbol.py         # SKL-01 deterministic
├── add-test.py              # SKL-02 agentic
├── summarize-diff.py        # SKL-03 agentic
├── port-py-to-voss.py       # SKL-04 agentic
├── audit-cognition.py       # SKL-05 agentic
├── voss-lint-as-skill.py    # SKL-06 deterministic
└── voss/                    # NEW subdirectory
    ├── __init__.py          # (may be omitted — not a Python package)
    ├── add-test.voss        # SKL-02 companion
    ├── summarize-diff.voss  # SKL-03 companion
    ├── port-py-to-voss.voss # SKL-04 companion
    └── audit-cognition.voss # SKL-05 companion

tests/skills/
├── __init__.py
├── conftest.py              # shared fixtures: isolated_state, seed_git_repo helper
├── test_skills_smoke.py     # per-skill deterministic assertions
└── fixtures/
    ├── rename-symbol/       # seed repo: foo.py with def foo(), caller.py
    ├── add-test/            # seed repo: target.py with public fn, no test yet
    ├── summarize-diff/      # seed repo: git history with staged diff
    ├── port-py-to-voss/     # seed repo: classify.py to translate
    ├── audit-cognition/     # seed repo: .voss/ initialized + stale state
    └── voss-lint/           # seed repo: bad.voss with known rule violations
```

### Pattern 1: SkillEntry Registration (the single integration point)

**What:** Add one `SkillEntry` per skill to `default_skill_registry()` in `skill_registry.py`.
**When to use:** Every new skill — this is the only place that must change in the registry file.

```python
# Source: voss/harness/skill_registry.py (lines 35-59, analyze registration as template)
def default_skill_registry() -> SkillRegistry:
    registry = SkillRegistry()

    def rename_symbol(ctx: Any, args: list[str]) -> None:
        from .skills.rename_symbol import run  # use underscored module name
        run(
            cwd=ctx.cwd,
            provider=ctx.provider,
            history=ctx.history,
            record=ctx.record,
            renderer=ctx.renderer,
            tools=ctx.tools,
            gate=ctx.gate,
            args=args,          # extra: skill-specific CLI args
        )

    registry.register(
        SkillEntry(
            id="rename-symbol",          # hyphenated slug for CLI
            description="Anchor + scope-aware rename across the repo.",
            handler=rename_symbol,
            mutating=True,
        )
    )
    # ... repeat for each skill
    return registry
```

**CRITICAL NOTE on module filenames:** Python module names cannot contain hyphens. The `SkillEntry.id` is hyphenated (`"rename-symbol"`) but the module filename must be underscored: `rename_symbol.py`, `add_test.py`, `summarize_diff.py`, `port_py_to_voss.py`, `audit_cognition.py`, `voss_lint_as_skill.py`. The `.voss` companion files use hyphens in their filenames since they are not Python modules.

### Pattern 2: Agentic Skill Handler (copy of analyze.py shape)

**What:** Import `run_turn`, call via `asyncio.run()`, pass full context kwargs.
**When to use:** SKL-02, SKL-03, SKL-04, SKL-05.

```python
# Source: voss/harness/skills/analyze.py (lines 25-107, adapted)
from __future__ import annotations
import asyncio
from pathlib import Path
from ..agent import run_turn

def run(*, cwd: Path, provider, history, record, renderer, tools, gate) -> None:
    prompt = (
        "Summarize the current git diff as a PR description with sections "
        "## Title, ## Summary, ## Changes."
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

### Pattern 3: Deterministic Skill Handler (no provider call)

**What:** Pure Python; use tools dict directly via `asyncio.run()` on individual tool calls, or subprocess.
**When to use:** SKL-01 (`rename-symbol`), SKL-06 (`voss-lint-as-skill`).

```python
# Source: voss/harness/tools.py — tool invocation pattern
import asyncio
from pathlib import Path

def run(*, cwd: Path, provider, history, record, renderer, tools, gate, args=None) -> None:
    # deterministic path — zero provider calls
    # call tools via their async interface wrapped in asyncio.run()
    hits = asyncio.run(tools["fs_grep"].invoke(pattern=r"\bfoo\b", glob="**/*.py"))
    # ... parse hits, call gate.check(), call tools["fs_edit"].invoke(...)
```

**IMPORTANT:** `ToolEntry.invoke(**kwargs)` is the correct call signature (not `invoke_dict`). The `invoke_dict(args: dict)` variant also exists but `invoke(**kwargs)` is cleaner.

### Pattern 4: FakeProvider for Agentic Skill Tests

**What:** A local `FakeProvider` class that implements `complete()` + `stream()` with canned `Plan` responses.
**When to use:** Every agentic skill test. Each test creates its own `FakeProvider(plan)` instance.

```python
# Source: tests/harness/test_agent_integration.py:30-99 (copy this shape)
from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage
from voss.harness.agent import Plan

class FakeProvider:
    def __init__(self, plan: Plan, cost: float = 0.001):
        self.plan = plan
        self.calls: list[dict] = []
        self._stream_index = 0

    async def complete(self, *, messages, model, response_format=None,
                       tools=None, temperature=1.0, max_tokens=None, timeout=None):
        # ... (see full shape in test_agent_integration.py:50-71)

    def stream(self, **kwargs):
        # first call emits canned plan; subsequent calls emit synthetic done plan
        async def _gen():
            yield TextDelta(text="…")
            yield ParsedPlan(plan=self.plan if self._stream_index == 0 else _done_plan)
            yield Usage(prompt_tokens=50, completion_tokens=50, cost_usd=self.cost)
            yield Done(stop_reason="end_turn")
        self._stream_index += 1
        return _gen()
```

### Pattern 5: SKL-06 Python API Path (preferred over subprocess for deterministic skill)

**What:** Call `voss.analyzer.analyze()` directly instead of shelling out to `voss check`.
**Why preferred:** Avoids subprocess overhead, avoids text parsing of CLI output, gives typed `Diagnostic` objects directly.

```python
# Source: voss/cli.py:293-303 (check command internals), voss/diagnostics.py:12-27
from voss.analyzer import analyze
from voss.diagnostics import Diagnostic
from voss.ast_nodes import Span

def _run_check(path: Path) -> list[Diagnostic]:
    from voss.cli import _parse_file, _walk_voss_sources  # internal helpers
    sources = _walk_voss_sources(path)
    all_diags: list[Diagnostic] = []
    for src in sources:
        program = _parse_file(src)
        result = analyze(program, source_path=str(src), emit_indexes=False)
        all_diags.extend(result.diagnostics)
    return all_diags
```

**Alternative (subprocess):** The harness already has the `voss_check` tool (`tools["voss_check"]`) that shells out and returns text. SKL-06 could call this tool, but then must parse text output. The direct Python API is strictly cleaner for a deterministic skill.

**LANDMINE:** `_parse_file` and `_walk_voss_sources` are private helpers in `voss/cli.py`. Either re-implement the `path.rglob("*.voss")` + `parse()` pattern inline in `voss_lint_as_skill.py`, or factor a thin `voss.checker` helper. Do NOT import private CLI helpers.

### Anti-Patterns to Avoid

- **Hyphenated module filename:** `rename-symbol.py` is not importable in Python. Use `rename_symbol.py`.
- **Direct filesystem writes in skills:** All writes must go through `fs_edit`/`fs_write` tools so the permission gate fires. SKL-01 calling `Path.write_text()` directly is a permission bypass.
- **Provider calls in deterministic skills:** SKL-01 and SKL-06 must not call `run_turn` or touch `provider`. This is the determinism invariant.
- **Importing private CLI helpers:** `voss/cli.py`'s `_parse_file`, `_walk_voss_sources` are underscore-prefixed internal helpers. SKL-06 should re-implement the file-walk inline or expose a thin helper via the public `voss` package.
- **audit-cognition writing architecture.md:** The skill must emit proposal text only. Any `fs_write` call targeting `architecture.md` is a bug.
- **Shell mode escalation:** `shell_run` is denied in `edit` mode (`permissions.py:61`). Skills must not try to escalate permissions to call shell.
- **Skipping `asyncio.run()` in the skill `run()` function:** Skill `run()` is a sync function (SkillHandler contract). Agentic skills must wrap `run_turn()` in `asyncio.run()`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Permission enforcement | Custom mode checks in skill | `PermissionGate.check()` via tools | Gate already handles plan/edit/auto tier; `fs_edit`/`fs_write` are `is_mutating=True` — gate fires automatically |
| Drift detection | Re-implement git diff counting | `cognition.drift_check(cwd, fm)` | Already handles `DRIFT_COMMITS=20`, `DRIFT_FILE_PCT=0.10`, `DRIFT_DAYS=7` thresholds |
| `.voss` diagnostics parsing | Parse text output of `voss check` | `voss.analyzer.analyze()` → `AnalysisResult.diagnostics` | Returns typed `Diagnostic` objects; no text parsing needed |
| Git diff capture | `subprocess.run(["git", "diff"])` inline | `tools["git_diff"].invoke(staged=False)` | Already handles sandbox + timeout + truncation |
| Test provider stub | Write new stub from scratch each test | Copy `FakeProvider` from `test_agent_integration.py` | Established pattern; handles both `complete()` and `stream()` paths |
| Git repo fixture creation | Custom `subprocess.run(["git", "init"])` per test | `git_repo` fixture from `tests/harness/conftest.py` | Already creates git repo with one commit; XDG sandboxed |

**Key insight:** The harness toolset is the skill execution surface — skills orchestrate tools, they don't do raw I/O.

---

## Codebase Investigation: Exact Signatures and Line Anchors

### `SkillEntry` and `SkillRegistry` (`voss/harness/skill_registry.py`)

```python
# Lines 7-59 (entire file is ~60 lines)
SkillHandler = Callable[[Any, list[str]], None]

@dataclass(frozen=True)
class SkillEntry:
    id: str                # hyphenated slug, e.g. "rename-symbol"
    description: str
    handler: SkillHandler  # signature: (ctx: Any, args: list[str]) -> None
    mutating: bool = False

class SkillRegistry:
    def register(self, entry: SkillEntry) -> None: ...
    def get(self, skill_id: str) -> SkillEntry | None: ...
    def ids(self) -> list[str]: ...   # sorted alphabetically
    def entries(self) -> list[SkillEntry]: ...  # sorted by id

def default_skill_registry() -> SkillRegistry:
    # Currently registers only "analyze" (mutating=True)
    # Handler lambda unpacks ctx.cwd/provider/history/record/renderer/tools/gate
    # and calls from .cli import _handle_analyze
```

**`SkillHandler` receives `ctx: Any` (a `ReplContext` or `SimpleNamespace`) and `args: list[str]`.**
The ctx unpacking pattern (not kwargs) is the existing contract. Each skill's inner function unpacks ctx fields and calls the module-level `run()` with kwargs.

### `run()` Signature in `analyze.py` (`voss/harness/skills/analyze.py:25-34`)

```python
def run(
    *,
    cwd: Path,
    provider,       # ModelProvider | None
    history,        # EpisodicMemory | None
    record,         # session_store.SessionRecord
    renderer,
    tools,          # dict[str, ToolEntry]
    gate,           # PermissionGate
) -> None:
```

This is the exact signature to copy for all 6 skill handlers. [VERIFIED: codebase read]

### `run_turn()` in `voss/harness/agent.py:412-428`

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

Import path from skill handlers: `from ..agent import run_turn`. [VERIFIED: analyze.py:19]

### Gated Tools (`voss/harness/tools.py`)

| Tool name | `is_mutating` | Signature (relevant args) | Use in T7 |
|-----------|--------------|--------------------------|-----------|
| `fs_read` | False | `(path: str)` | SKL-01 reads before rename |
| `fs_glob` | False | `(pattern: str)` | SKL-01 discovers files |
| `fs_grep` | False | `(pattern: str, glob: str = "**/*")` | SKL-01 finds symbol sites |
| `fs_write` | True | `(path: str, content: str)` | SKL-04 writes generated `.voss` |
| `fs_edit` | True | `(path: str, old: str, new: str)` | SKL-01 renames, SKL-02 plants test |
| `git_diff` | False | `(staged: bool = False, path: str = "")` | SKL-03 gets diff |
| `voss_check` | False | `(path: str = ".")` | Alternative path for SKL-06 (subprocess) |
| `shell_run` | True | `(cmd: str)` | NOT usable in edit mode (denied by mode_allows) |

**Permission model (`voss/harness/permissions.py:44-64`):**
- `plan` mode: denies ALL `is_mutating=True` tools → message `"denied by mode plan"`
- `edit` mode: allows `fs_write`/`fs_edit`, explicitly denies `shell_run`
- `auto` mode: allows everything (caller-side approval)

**`mode_allows()` at line 49** is the authoritative tier check. Skill-level code never needs to replicate this — the gate fires on every tool call automatically via the agent's tool dispatch. [VERIFIED: permissions.py full read]

### `PermissionGate.check()` (`voss/harness/permissions.py:169-194`)

```python
def check(
    self,
    tool_name: str,
    args: dict,
    *,
    is_mutating: bool = False,
    is_network: bool = False,
) -> tuple[bool, str]:
```

The agent loop calls `gate.check()` before each tool invocation. For deterministic skills calling tools directly, the pattern is `asyncio.run(tools["fs_grep"].invoke(...))` — note that `ToolEntry.invoke(**kwargs)` does NOT call the gate. For deterministic skills that need gate enforcement, they must call `gate.check(tool_name, args, is_mutating=entry.is_mutating)` explicitly before invoking. **This is a landmine for SKL-01.** Recommendation: SKL-01 uses `PermissionGate.check()` before every `fs_edit` call.

### `cognition.*` APIs for SKL-05 (`voss/harness/cognition.py`)

```python
# Available drift APIs (all confirmed at lines 63, 253, 278, 576, 601, 653)

@dataclass
class DriftStatus:
    is_stale: bool
    head_diverged_by: int
    file_count_delta: int
    days_elapsed: int
    reason: str = ""

def load(cwd: Path, *, token_count: callable | None = None) -> CognitionBundle: ...
    # Returns CognitionBundle with .architecture_frontmatter: ArchitectureFrontmatter | None

def drift_check(cwd: Path, fm: ArchitectureFrontmatter) -> DriftStatus: ...
    # Thresholds: DRIFT_COMMITS=20, DRIFT_FILE_PCT=0.10, DRIFT_DAYS=7

def build_bootstrap_inventory(cwd: Path) -> dict: ...
    # Returns project inventory (same data analyze uses for prompting)

def bootstrap_prompt(inventory: dict, *, target_path: str) -> str: ...
    # Builds the full LLM prompt for architecture analysis
```

**SKL-05 implementation sketch:**
1. `bundle = cognition.load(cwd)` — load existing cognition state
2. If not `bundle.initialized`: emit "cognition not initialized — run /analyze first"
3. If `bundle.architecture_frontmatter is None`: cannot check drift
4. `drift = cognition.drift_check(cwd, bundle.architecture_frontmatter)` — get drift status
5. Construct prompt mentioning drift reason + ask LLM to propose a 1-paragraph update
6. Drive `run_turn(prompt, ...)` — proposal printed via renderer to stdout
7. Explicitly do NOT call `voss_md.write_fence_body()`

### `voss check` Diagnostic Fields for SKL-06 (`voss/diagnostics.py`)

```python
@dataclass(frozen=True, slots=True)
class Diagnostic:
    severity: DiagnosticSeverity  # Literal["warning", "error"]
    code: str                     # e.g. "E001", "W003" — the rule ID
    message: str                  # human-readable description
    span: Span                    # location
    hint: str | None = None       # optional suggested fix

@dataclass(frozen=True, slots=True)
class Span:
    file: str       # source file path (string, not Path)
    line_start: int
    col_start: int
    line_end: int
    col_end: int
    synthetic: bool = False
```

**SKL-06 frozen JSON schema design:**

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

Field mapping: `span.file` → `"file"`, `span.line_start` → `"line"`, `span.col_start` → `"col"`, `code` → `"rule"`, `severity` → `"severity"`, `message` → `"msg"`, `hint` → `"hint"` (nullable). The `line_end`/`col_end`/`synthetic` fields are omitted from the schema — they add no value for M11 consumption.

**Implementation path:** Parse `.voss` files using `voss.parser.parse()` directly (avoid importing private `_parse_file`), call `voss.analyzer.analyze()`, map `AnalysisResult.diagnostics` to the schema, serialize to JSON. This is a zero-subprocess path. [VERIFIED: python3 import test confirmed `from voss.analyzer import analyze; from voss.diagnostics import Diagnostic` is importable]

### CLI Surfaces (`voss/harness/cli.py`)

**Discoverability verification:** Adding a `SkillEntry` to `default_skill_registry()` is sufficient. No extra wiring needed.

- `/skills` → `_skills()` at line 865 → calls `_print_skills(ctx)` at line 464 → iterates `ctx.skill_registry.entries()`
- `/skill <id> [args...]` → `_skill()` at line 868 → `ctx.skill_registry.get(args[0])` → `entry.handler(ctx, args[1:])`
- `voss skills` → `skills_cmd()` at line 1769 → calls `_print_skills(ctx)` from `_extension_context()`
- `voss skill run <id> [args...]` → `skill_run_cmd()` at line 1786 → `_extension_context()` → `entry.handler(ctx, list(args))`

`_extension_context()` at line 1698 calls `default_skill_registry()` which picks up new entries automatically. [VERIFIED: cli.py full read]

**Post-T7 count:** `voss skills` will list 7 entries: `analyze` (existing, sorts first alphabetically) + 6 new.

### T5 D-12 Permission Precedent

From `permissions.py:61`: `mode_allows()` in `edit` mode explicitly returns `(False, "denied by mode edit")` when `tool_name == "shell_run"`. This is the pattern for the explicit-deny precedent. T7 does NOT add new denials — skills compose existing tools, and the existing gate handles all mode-tier enforcement automatically.

---

## Skill-by-Skill Implementation Notes

### SKL-01 `rename-symbol` (deterministic, mutating)

**Scoping engine recommendation: anchor + `fs_grep`/`fs_edit` heuristic** (Claude's Discretion).

**Rationale:** No Python AST usage exists anywhere in the Voss codebase [VERIFIED: grep found 0 matches for `import ast`/`ast.parse`/`ast.walk` in `voss/`]. Python's AST approach requires parsing every source file, handling multi-file projects, managing import graph resolution for cross-file renames — all substantial complexity. The existing `fs_grep` tool already does recursive regex search with file:line output. The `fs_edit` tool handles unique-match enforcement. For a v0.1 skill, an anchor+heuristic approach is appropriate:

1. `args[0]` = old name, `args[1]` = new name (CLI positional args)
2. `fs_grep(pattern=r"\b{old}\b", glob="**/*.py")` → find all occurrences
3. Deduplicate by file
4. For each file: `fs_read(path)` → count occurrences → call `fs_edit` per unique context (or `fs_edit_many` for multiple in one file)
5. Check `gate.check("fs_edit", {"path": path, "old": old_text, "new": new_text}, is_mutating=True)` before each edit in the deterministic path

**Landmine:** `ToolEntry.invoke(**kwargs)` bypasses the gate in direct (non-agent) calls. For SKL-01, since it's deterministic (not going through `run_turn`), the skill must explicitly call `gate.check()` before each `fs_edit`/`fs_write` invocation.

**Test fixture `fixtures/rename-symbol/`:**
- `foo.py`: contains `def foo(): pass`
- `caller.py`: contains `from foo import foo; foo()`
- Expected patch: `foo` → `bar` in both files
- Assertion: `git diff` == known unified diff

### SKL-02 `add-test` (agentic, mutating)

- Test-framework detection: pytest (confirmed — `pyproject.toml [tool.pytest.ini_options]` + `asyncio_mode = "auto"`, markers, `testpaths = ["tests"]`).
- Prompt construction: instruct the agent to find a public function in the fixture repo, generate a pytest test function with a failing `assert False` placeholder, and write it to `tests/test_<module>.py` via `fs_write`.
- Verification: `pytest --collect-only tests/test_<module>.py` exits 0 and lists the new test name.

**Test fixture `fixtures/add-test/`:**
- `target.py`: contains `def add(a, b): return a + b` (no test yet)
- Expected: after skill runs, `tests/test_target.py` exists, `pytest --collect-only` finds `test_add`

### SKL-03 `summarize-diff` (agentic, read-only)

- Prompt: "Summarize the current git diff as a pull request description. Output ONLY structured markdown with sections ## Title, ## Summary, and ## Changes."
- The agent calls `git_diff()` tool to get the diff, then composes the markdown in `final_when_done`.
- Renderer prints the final. No file writes.

**Test fixture `fixtures/summarize-diff/`:**
- Git repo with at least one unstaged change (e.g., a modified `README.md`)
- FakeProvider plan emits `final_when_done` containing `## Title`, `## Summary`, `## Changes`
- Assertion: output is non-empty, contains all three section headers

### SKL-04 `port-py-to-voss` (agentic, mutating)

- Target shapes: `samples/classify.voss` (simple fn + `probable<T>` + confidence gate), `samples/support.voss` (`prompt`, `memory.episodic`, `match similar`), `samples/research.voss` (`agent`, `spawn`, `gather`, `within/fallback`, `try/catch`).
- Prompt: ask the LLM to translate the input Python file to `.voss` using the appropriate sample shape as a guide, then write the `.voss` output via `fs_write`.
- The companion `.voss` artifact for this skill itself should model the `classify` shape (simplest — fn + confidence check).
- Verification: `voss check <generated_file>` exits 0.

**Test fixture `fixtures/port-py-to-voss/`:**
- `classify_intent.py`: simple function returning a string based on input (maps to `classify.voss` shape)
- FakeProvider returns a plan that calls `fs_write("classify_intent.voss", <valid_voss_content>)`
- Assertion: `voss check classify_intent.voss` exits 0

### SKL-05 `audit-cognition` (agentic, read-only)

- Implementation: load cognition bundle → compute drift → build proposal prompt → run_turn → emit proposal only.
- The prompt MUST include an explicit instruction: "Do NOT write to any file. Output your proposal as a paragraph starting with 'PROPOSAL:'. "
- **Critical:** `run_turn` is called with a toolset that includes only read-only tools (or the mutating tools are gate-denied in the current mode). The skill does not manually strip tools — it relies on the gate mode to prevent writes. If the caller is in `plan` mode, mutating tools are denied automatically.
- Verification: the FakeProvider's `final_when_done` contains "PROPOSAL:" or similar marker; `architecture.md` (or VOSS.md architecture fence) is unchanged after the skill runs.

### SKL-06 `voss-lint-as-skill` (deterministic, read-only)

- Direct Python API approach: import `voss.analyzer.analyze` + `voss.parser.parse` (public API), walk the path, collect `Diagnostic` objects, serialize to frozen JSON schema.
- Output via `click.echo(json.dumps(schema_dict, indent=2))` — to stdout. The renderer is not used for structured JSON (renderer is for human-readable streaming content).
- Schema is FROZEN once written — treat as M11 contract.
- `args[0]` = path to check (default: `.` = entire project `.voss` files)

**LANDMINE for SKL-06:** The `voss/parser.py` module's public entry point is `parse()` but the `voss/cli.py` wraps it in `_parse_file()` which handles click error formatting. For the skill, use the parser directly:

```python
from voss.parser import parse   # check if this is public
```

Verify: `grep -n "^def parse\|^def _parse" /Users/benjaminmarks/Projects/Voss/voss/parser.py` — the public API surface.

---

## `.voss` Companion File Design

Companion `.voss` files at `voss/harness/skills/voss/<id>.voss` must pass `voss check`. They are dogfood demonstrations, not the exec path.

### Available `.voss` constructs (confirmed from samples + agent files)

| Construct | Example source |
|-----------|---------------|
| `fn`, `return`, `let` | All sample files |
| `probable<T>`, `ask()`, `@ p >= N.NN` | `classify.voss:5-10`, `loop.voss:13-22` |
| `ctx(budget: N tokens) { ... }` | `loop.voss:13`, `planner.voss:11` |
| `prompt Block { "..." }` | `support.voss:3-5` |
| `memory.episodic(capacity: N)` | `support.voss:7` |
| `match ... { case similar(...) => }` | `support.voss:11-27` |
| `agent Name(args) -> T { system: ..., tools: [...] }` | `research.voss:6-19` |
| `spawn Agentname(arg)` | `research.voss:38`, `loop.voss:73` |
| `gather(list, timeout: Ns)` | `research.voss:39`, `loop.voss:73` |
| `within budget(...) { } fallback { }` | `research.voss:41-46` |
| `try { } catch e { }` | `research.voss:12-15`, `reviewer.voss:16-26` |
| `use module::path` | `loop.voss:2-11`, `executor.voss:2-7` |
| `include identifier` | `loop.voss:30-31` |
| `yield ask(...)` | `research.voss:18`, `support.voss:25` |
| `print(...)` | `classify.voss:14`, `research.voss:49` |

### Companion shape recommendations

- **`add-test.voss`**: `fn findPublicFn(path: string) -> string` with `probable<string>` + confidence check. Models `classify.voss` shape.
- **`summarize-diff.voss`**: `fn summarizeDiff(diff: string) -> string` with `ctx(budget: 3000 tokens) { yield ask(...) }`. Simple fn shape.
- **`port-py-to-voss.voss`**: `fn translatePython(pySource: string) -> string` with `ctx(budget: 6000 tokens) { ... }` + `try/catch`. Models `research.voss` shape.
- **`audit-cognition.voss`**: `fn proposeCognitionUpdate(drift: string) -> string` with `ctx(budget: 2000 tokens) { yield ask(...) }`. Keep it simple.

---

## Common Pitfalls

### Pitfall 1: Hyphenated module filename
**What goes wrong:** `from .skills.rename-symbol import run` is a Python syntax error.
**Why it happens:** `SkillEntry.id` uses hyphens (for CLI display), but Python module names cannot.
**How to avoid:** Use underscored filenames: `rename_symbol.py`, `voss_lint_as_skill.py`, etc.
**Warning signs:** `ImportError: No module named 'skills.rename-symbol'` at skill invocation.

### Pitfall 2: Gate bypass in deterministic skills
**What goes wrong:** SKL-01 calls `tools["fs_edit"].invoke(...)` directly without checking the gate → write succeeds in `plan` mode, violating D-09/D-11.
**Why it happens:** `ToolEntry.invoke()` is a raw async call. The gate is only called automatically by the agent loop (inside `run_turn`). Deterministic skills operate outside `run_turn`.
**How to avoid:** Always call `gate.check(tool_name, args_dict, is_mutating=True)` before any mutating tool invocation in deterministic skills. Return early with a user-visible message if `allowed=False`.
**Warning signs:** Edits succeed in test with `PermissionGate(mode="plan")`.

### Pitfall 3: audit-cognition writing architecture.md
**What goes wrong:** The agentic skill produces a plan with `fs_write` targeting `VOSS.md` or `.voss/architecture.md`.
**Why it happens:** The LLM, not given a clear constraint, may decide to "apply" its proposal.
**How to avoid:** Two layers of defense: (1) prompt explicitly forbids writing ("Do NOT write to any file"); (2) the test runs with a read-only gate (or checks that `architecture.md`/`VOSS.md` is unchanged post-run).
**Warning signs:** `VOSS.md` mtime changes after `audit-cognition` runs in the test.

### Pitfall 4: FakeProvider only implementing `complete()`, not `stream()`
**What goes wrong:** `run_turn` calls `provider.stream(...)` (T1-05 change), not `provider.complete()`. A FakeProvider without `stream()` raises `AttributeError`.
**Why it happens:** Pre-T1 tests used `complete()`; post-T1 the iteration loop exclusively calls `stream()`.
**How to avoid:** Copy the full `FakeProvider` shape from `test_agent_integration.py:30-99` which implements both.
**Warning signs:** `AttributeError: 'FakeProvider' object has no attribute 'stream'`.

### Pitfall 5: `.voss` companion file failing `voss check`
**What goes wrong:** The companion `.voss` artifact has a syntax or analyzer error, CI fails.
**Why it happens:** `.voss` syntax has specific constraints (e.g., `use` statements must reference valid paths; `probable<T>` requires specific type annotations).
**How to avoid:** Run `python -m voss.cli check <file>` locally before committing. Use the simplest construct that demonstrates the concept — `fn` + `ctx(budget)` + `ask()` is sufficient for all 4 companions.
**Warning signs:** CI `voss check voss/harness/skills/voss/` step exits 1.

### Pitfall 6: `voss skills` showing < 7 entries
**What goes wrong:** A skill registration is missing from `default_skill_registry()`.
**Why it happens:** The handler lambda in `default_skill_registry()` and the `SkillEntry` registration are written correctly but one was accidentally omitted.
**How to avoid:** The smoke test should assert `len(registry.ids()) == 7` (or >= 7) as the first check.

### Pitfall 7: Importing `_parse_file` from `voss/cli.py` for SKL-06
**What goes wrong:** `from voss.cli import _parse_file` — this is a private CLI implementation detail. Coupling to it creates a fragile dependency.
**How to avoid:** Implement the file walk inline (`path.rglob("*.voss")`) and call `voss.parser.parse()` directly. Verify the public parser API.

---

## Test Seam: FakeProvider Anatomy

The `FakeProvider` pattern used across M4/M5 tests is the exact seam for T7 agentic skill tests. Key properties:

1. **`stream()` is the primary call path** (post-T1-05). Must yield `TextDelta`, `ParsedPlan`, `Usage`, `Done` in that order.
2. **`_stream_index` guards first vs. follow-up calls.** First call emits the canned plan; subsequent calls emit a synthetic done plan so the iteration loop terminates.
3. **`Plan` must have `final_when_done` non-empty** for the loop to recognize it as a terminating plan.
4. **`PermissionGate(auto_yes=True)`** is the test gate — no interactive prompts.
5. **`PlainRenderer()`** for tests — no TUI, no diff modal.

For agentic skills that need to assert on tool invocations (e.g., `summarize-diff` calls `git_diff`), the plan's `steps` should include the tool call:

```python
plan = Plan(
    rationale="get diff and summarize",
    steps=[ToolCall(name="git_diff", args={})],
    confidence=0.90,
    final_when_done="## Title\nfoo\n## Summary\nbar\n## Changes\nbaz",
)
```

The harness will invoke `git_diff`, capture the result, feed it back to the FakeProvider's second stream call (the synthetic done plan already has the correct `final_when_done`).

---

## CI Configuration Requirements

**Current CI (`ci.yml:47`):**
```yaml
- name: voss check harness sources (M4 DOG-06)
  run: python -m voss.cli check voss/harness/agent/
- run: python -m voss.cli check voss-demos/
```

**Required T7 addition:**
```yaml
- name: voss check skills voss companions (T7)
  run: python -m voss.cli check voss/harness/skills/voss/
```

This must be added to the `stub` job (line 32) in `.github/workflows/ci.yml`. The CI job installs `pip install -e ".[dev]"` which makes `voss check` available.

Additionally, `tests/skills/test_skills_smoke.py` will be picked up automatically by `pytest -q -m "not live"` since `testpaths = ["tests"]` is already configured.

**No new CI markers needed** — skill tests are deterministic (no `@pytest.mark.live`, no `@pytest.mark.slow`).

---

## State of the Art

| Aspect | Current State | T7 Adds |
|--------|--------------|---------|
| Skill registry | 1 entry (`analyze`) | +6 entries (total 7) |
| Skill handlers | `voss/harness/skills/analyze.py` only | 6 new handler modules |
| `.voss` companions for skills | None | 4 companion files in `voss/harness/skills/voss/` |
| Skill test coverage | None (confirmed: `find tests -name "*skill*"` = 0 results) | New `tests/skills/` package |
| `voss check` CI scope | `voss/harness/agent/` + `voss-demos/` | + `voss/harness/skills/voss/` |

---

## Assumptions Log

A1 and A2 were resolved during research:
- A1 RESOLVED: `voss.parser.parse(source: str, file: str = "<string>") -> Program` is a public function at `voss/parser.py:791`. [VERIFIED: grep]
- A2 RESOLVED: `SessionRecord.model: str` is a confirmed field at `voss/harness/session.py:154`. [VERIFIED: read]

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A3 | `asyncio.run()` is safe to call from the skill `run()` function (no running event loop at call site) | Agentic skill pattern | If called from within an async context (unlikely for slash commands), would raise RuntimeError |

**If the table is empty of unresolved items:** A1/A2 verified above; only A3 remains as a low-probability assumption (slash commands are sync-called from the REPL; no running event loop at that call site).

---

## Open Questions

All open questions were resolved during research:

1. **`voss.parser.parse()` public API — RESOLVED**
   - `voss/parser.py:791` defines `def parse(source: str, file: str = "<string>") -> Program:` — public function. [VERIFIED: grep]
   - SKL-06 implementation: `from voss.parser import parse` is valid.

2. **`SessionRecord.model` field — RESOLVED**
   - `voss/harness/session.py:154` confirms `model: str` is a `SessionRecord` field. [VERIFIED: read]
   - `record.model` in skill handlers is correct.

---

## Environment Availability

| Dependency | Required By | Available | Notes |
|------------|------------|-----------|-------|
| Python 3.11+ | All skills | ✓ | Project requires Python ≥ 3.11 (pyproject.toml) |
| pytest | Test suite | ✓ | In `[dev]` extras; `asyncio_mode = "auto"` configured |
| `voss check` CLI | CI gate + SKL-06 | ✓ | `pip install -e ".[dev]"` installs it |
| `git` | `git_repo` fixture + SKL-01/SKL-03 | ✓ | Used throughout existing tests |
| `asyncio` | Agentic skill `asyncio.run()` | ✓ | stdlib |

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (with `asyncio_mode = "auto"`) |
| Config file | `pyproject.toml [tool.pytest.ini_options]` |
| Quick run command | `pytest tests/skills/ -q` |
| Full suite command | `pytest -q -m "not live"` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SKL-01 | `rename-symbol` produces correct patch | deterministic unit | `pytest tests/skills/test_skills_smoke.py::test_rename_symbol -x` | ❌ Wave 0 |
| SKL-02 | `add-test` creates collectable test | deterministic unit | `pytest tests/skills/test_skills_smoke.py::test_add_test -x` | ❌ Wave 0 |
| SKL-03 | `summarize-diff` output has PR sections | deterministic unit | `pytest tests/skills/test_skills_smoke.py::test_summarize_diff -x` | ❌ Wave 0 |
| SKL-04 | `port-py-to-voss` output passes `voss check` | deterministic unit | `pytest tests/skills/test_skills_smoke.py::test_port_py_to_voss -x` | ❌ Wave 0 |
| SKL-05 | `audit-cognition` emits proposal, no write | deterministic unit | `pytest tests/skills/test_skills_smoke.py::test_audit_cognition -x` | ❌ Wave 0 |
| SKL-06 | `voss-lint-as-skill` JSON schema valid + known findings | deterministic unit | `pytest tests/skills/test_skills_smoke.py::test_voss_lint -x` | ❌ Wave 0 |
| All | `voss skills` lists 7 entries | smoke | `pytest tests/skills/test_skills_smoke.py::test_registry_count -x` | ❌ Wave 0 |
| D-05 | `.voss` companions pass `voss check` | CI shell gate | `python -m voss.cli check voss/harness/skills/voss/` | ❌ Wave 0 (files) |

### Sampling Rate

- **Per task commit:** `pytest tests/skills/ -q`
- **Per wave merge:** `pytest -q -m "not live"`
- **Phase gate:** Full suite green + `voss check voss/harness/skills/voss/` exits 0 before verify-work

### Wave 0 Gaps

- [ ] `tests/skills/__init__.py` — empty package marker
- [ ] `tests/skills/conftest.py` — `isolated_state` autouse (port from harness conftest), `seed_git_repo()` helper, `FakeProvider` class (copy from test_agent_integration.py)
- [ ] `tests/skills/test_skills_smoke.py` — stub test functions (one per SKL, `pytest.fail("not yet")`)
- [ ] `tests/skills/fixtures/rename-symbol/` — `foo.py`, `caller.py` seed files
- [ ] `tests/skills/fixtures/add-test/` — `target.py` seed file
- [ ] `tests/skills/fixtures/summarize-diff/` — git repo with staged change
- [ ] `tests/skills/fixtures/port-py-to-voss/` — `classify_intent.py` seed
- [ ] `tests/skills/fixtures/audit-cognition/` — pre-initialized `.voss/` + stale state
- [ ] `tests/skills/fixtures/voss-lint/` — `bad.voss` with known seeded error
- [ ] `voss/harness/skills/voss/` directory + `__init__.py` (or just directory)
- [ ] CI step: `python -m voss.cli check voss/harness/skills/voss/` in `ci.yml`

---

## Security Domain

> `security_enforcement` is not set to false — section included.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No | Skills inherit session auth; no new auth surface |
| V3 Session Management | No | Skills use existing session context |
| V4 Access Control | Yes | `PermissionGate` mode-tier enforcement (existing) |
| V5 Input Validation | Yes | `fs_grep` pattern compiled via `re.compile()` with error handling; `fs_edit` unique-match enforcement |
| V6 Cryptography | No | No new crypto surface |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Skill bypasses gate (calls `ToolEntry.invoke()` without `gate.check()`) | Elevation of Privilege | Deterministic skills must call `gate.check()` explicitly before mutating tool calls |
| `audit-cognition` writes architecture file despite read-only contract | Tampering | Prompt constraint + test assertion that file is unchanged post-run |
| SKL-01 renames outside `cwd` via path traversal | Tampering | `jail_path()` in `fs_edit` already enforces cwd sandbox |
| Invalid regex in SKL-01 symbol pattern | DoS | `fs_grep` catches `re.error` and returns error string |

---

## Sources

### Primary (HIGH confidence)

- `voss/harness/skill_registry.py` — exact `SkillEntry`, `SkillHandler`, `SkillRegistry` shapes; `default_skill_registry()` body [VERIFIED: full file read]
- `voss/harness/skills/analyze.py` — exact `run()` signature; agentic pattern with `run_turn`; staged-write via `voss_md.write_fence_body` [VERIFIED: full file read]
- `voss/harness/tools.py` — all gated tool signatures, `is_mutating` flags, `make_toolset()` [VERIFIED: full file read]
- `voss/harness/permissions.py` — `mode_allows()`, `PermissionGate.check()`, `READ_ONLY`/`WRITE`/`SHELL` sets, plan/edit/auto behavior [VERIFIED: full file read]
- `voss/harness/cognition.py` — `load()`, `drift_check()`, `DriftStatus`, `build_bootstrap_inventory()`, `bootstrap_prompt()` [VERIFIED: signatures read]
- `voss/diagnostics.py` — `Diagnostic` dataclass fields + `Span` fields [VERIFIED: full file read + python3 import test]
- `voss/analyzer.py:755` — `analyze()` public function signature [VERIFIED: read]
- `voss/cli.py:267-311` — `voss check` command internals; `_print_diagnostics`; `_walk_voss_sources` [VERIFIED: read]
- `voss/harness/cli.py` — `_print_skills`, `_skill`, `_skills`, `SlashCommand` registrations, `skills_cmd`, `skill_group`, `skill_run_cmd`, `_extension_context` [VERIFIED: multiple reads]
- `tests/harness/test_agent_integration.py:30-99` — `FakeProvider` canonical shape [VERIFIED: read]
- `tests/harness/conftest.py` — `isolated_state`, `git_repo` fixtures [VERIFIED: read]
- `.github/workflows/ci.yml` — current `voss check` gates + pytest invocation [VERIFIED: full file read]
- `pyproject.toml [tool.pytest.ini_options]` — pytest config, markers [VERIFIED: read]
- `samples/classify.voss`, `samples/support.voss`, `samples/research.voss` — `.voss` constructs available [VERIFIED: full file reads]
- `voss/harness/agent/loop.voss`, `executor.voss`, `reviewer.voss`, `planner.voss` — dogfood `.voss` constructs [VERIFIED: full file reads]

### Secondary (MEDIUM confidence)

- `voss/ast_nodes.py:8-20` — `Span` field names confirmed [VERIFIED: read]
- `python3 -c "from voss.analyzer import analyze; from voss.diagnostics import Diagnostic"` — import reachability confirmed [VERIFIED: shell execution]

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all confirmed by direct codebase read; zero new dependencies
- Architecture: HIGH — registration path, CLI wiring, permission gate all read directly
- Pitfalls: HIGH — landmines derived from reading actual code paths, not training data
- `.voss` companion shapes: HIGH — all constructs verified against actual sample files
- SKL-06 JSON schema: HIGH — `Diagnostic` fields confirmed via import test
- Open Questions: RESOLVED — parser public API (`voss/parser.py:791`) and `SessionRecord.model` (`voss/harness/session.py:154`) both verified during research

**Research date:** 2026-05-17
**Valid until:** 2026-06-17 (30 days; stable internal codebase)
