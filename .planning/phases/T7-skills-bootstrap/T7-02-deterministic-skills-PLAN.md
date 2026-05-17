---
phase: T7-skills-bootstrap
plan: 02
type: execute
wave: 2
depends_on: [T7-01]
files_modified:
  - voss/harness/skills/rename_symbol.py
  - voss/harness/skills/voss_lint_as_skill.py
  - voss/harness/skill_registry.py
  - tests/skills/test_skills_smoke.py
autonomous: true
requirements: [SKL-01, SKL-06]

must_haves:
  truths:
    - "Running `rename-symbol <old> <new>` in edit/auto mode renames every `\\bold\\b` occurrence across the repo's `*.py` files through the gated `fs_edit` tool"
    - "Running `rename-symbol` in `plan` mode performs ZERO mutations and prints a clean refusal — no escalation, no bypass, target files byte-identical afterward"
    - "Running `voss-lint-as-skill <path>` emits a single JSON object on stdout with keys `version` and `findings`, each finding having `file,line,col,rule,severity,msg,hint`"
    - "`voss-lint-as-skill` finds the seeded violation in `tests/skills/fixtures/voss-lint/bad.voss` with zero provider calls"
    - "`default_skill_registry()` registers `rename-symbol` (mutating=True) and `voss-lint-as-skill` (mutating=False) in addition to `analyze`"
    - "`tests/skills/test_skills_smoke.py::test_rename_symbol` and `::test_voss_lint` pass green"
  artifacts:
    - path: "voss/harness/skills/rename_symbol.py"
      provides: "SKL-01 deterministic mutating rename handler with explicit gate.check before every fs_edit"
      contains: "def run"
      min_lines: 40
    - path: "voss/harness/skills/voss_lint_as_skill.py"
      provides: "SKL-06 deterministic read-only lint handler emitting the frozen M11 JSON schema"
      contains: "def run"
      min_lines: 35
    - path: "voss/harness/skill_registry.py"
      provides: "two new SkillEntry registrations in default_skill_registry()"
      contains: "rename-symbol"
    - path: "tests/skills/test_skills_smoke.py"
      provides: "test_rename_symbol + test_voss_lint bodies turned green (test_registry_count stays RED until T7-04)"
      contains: "def test_rename_symbol"
  key_links:
    - from: "voss/harness/skill_registry.py"
      to: "voss.harness.skills.rename_symbol.run"
      via: "default_skill_registry() inner handler imports + calls run(...)"
      pattern: "from .skills.rename_symbol import run"
    - from: "voss/harness/skill_registry.py"
      to: "voss.harness.skills.voss_lint_as_skill.run"
      via: "default_skill_registry() inner handler imports + calls run(...)"
      pattern: "from .skills.voss_lint_as_skill import run"
    - from: "voss/harness/skills/rename_symbol.py"
      to: "voss.harness.permissions.PermissionGate.check"
      via: "explicit gate.check('fs_edit', ..., is_mutating=True) before each fs_edit invoke"
      pattern: "gate\\.check\\("
    - from: "voss/harness/skills/voss_lint_as_skill.py"
      to: "voss.parser.parse + voss.analyzer.analyze"
      via: "direct public Python API, inline rglob, no private cli helpers"
      pattern: "from voss\\.parser import parse"
---

<objective>
Implement the two deterministic, Python-only skills (D-06: no `.voss`
companions): SKL-01 `rename-symbol` (mutating, anchor + grep/edit heuristic)
and SKL-06 `voss-lint-as-skill` (read-only, frozen M11 JSON diagnostics).
Register both in `default_skill_registry()` and turn their two smoke tests
green.

Purpose: These are the provider-free skills — zero LLM dependency (D-08), so
they give the fastest hermetic green signal in the phase and land the
permission-gate invariant (a deterministic mutating skill that runs OUTSIDE
`run_turn` MUST self-enforce the gate, RESEARCH landmine #3 / Pitfall 2).
SKL-06's JSON schema becomes the frozen M11 contract (D-12).

Output: `voss/harness/skills/rename_symbol.py`,
`voss/harness/skills/voss_lint_as_skill.py`, two `SkillEntry` registrations
in `voss/harness/skill_registry.py`, and green bodies for
`test_rename_symbol` + `test_voss_lint` in `tests/skills/test_skills_smoke.py`.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/T7-skills-bootstrap/T7-CONTEXT.md
@.planning/phases/T7-skills-bootstrap/T7-RESEARCH.md
@.planning/phases/T7-skills-bootstrap/T7-PATTERNS.md
@.planning/phases/T7-skills-bootstrap/T7-01-test-scaffold-PLAN.md

<interfaces>
<!-- Contracts the executor needs. Extracted from live source — no codebase exploration required. -->

SkillEntry / default_skill_registry — voss/harness/skill_registry.py (live, full file)
  - `@dataclass(frozen=True) class SkillEntry: id: str; description: str; handler: SkillHandler; mutating: bool = False`
  - `SkillHandler = Callable[[Any, list[str]], None]` — handler signature is
    `(ctx: Any, args: list[str]) -> None`.
  - `SkillRegistry.register(entry)`, `.get(id)`, `.ids()` (sorted), `.entries()`.
  - `default_skill_registry()` currently builds `registry`, defines an inner
    `def analyze(ctx, _args)` that does `from .cli import _handle_analyze`
    then calls it with `cwd/provider/history/record/renderer/tools/gate`
    unpacked from `ctx`, registers ONE `SkillEntry(id="analyze", ...,
    mutating=True)`, and `return registry`. The two new registrations are
    inserted between the `analyze` registration and `return registry`.

run() handler signature — voss/harness/skills/analyze.py:25-34 (live)
  - `def run(*, cwd: Path, provider, history, record, renderer, tools, gate) -> None:`
  - Deterministic skills ADD `args: list[str] | None = None` as a final
    keyword-only param (T7-PATTERNS lines 254-264 / 360-370). The registry's
    inner handler passes `args=args`.

PermissionGate.check — voss/harness/permissions.py:169 (live)
  - `def check(self, tool_name: str, args: dict, *, is_mutating: bool = False, is_network: bool = False) -> tuple[bool, str]:`
  - Returns `(allowed: bool, reason: str)`. In `plan` mode any
    `is_mutating=True` call returns `(False, "denied by mode plan")`
    (`mode_allows` at permissions.py:49-64). `edit`/`auto` allow `fs_edit`.
  - `PermissionGate(auto_yes=True)` is the hermetic test gate; its default
    mode allows mutation. `PermissionGate(mode="plan")` is the refusal case.

ToolEntry.invoke — voss/harness/tools.py:20-50 (live)
  - `ToolEntry` has `descriptor`, `is_mutating: bool`. `def invoke(self,
    **kwargs) -> Any` and `def invoke_dict(self, args: dict) -> Any`.
    `invoke(**kwargs)` is an async coroutine — call sites wrap it in
    `asyncio.run(...)`.
  - LANDMINE (RESEARCH landmine #3 / Pitfall 2): `invoke()` does NOT call the
    permission gate. The gate only fires automatically inside `run_turn`'s
    tool dispatch. Deterministic skills run OUTSIDE `run_turn`, so they MUST
    call `gate.check(...)` themselves before every mutating invoke.
  - Toolset names (voss/harness/tools.py:360-375): `fs_grep`
    (is_mutating=False, `invoke(pattern: str, glob: str = "**/*")`),
    `fs_read` (False, `invoke(path: str)`), `fs_edit` (is_mutating=True,
    `invoke(path: str, old: str, new: str)`).

voss.parser.parse — voss/parser.py:791 (live, PUBLIC)
  - `def parse(source: str, file: str = "<string>") -> Program:`

voss.analyzer.analyze — voss/analyzer.py:755 (live, PUBLIC)
  - Called by `analyze.py`'s reference pattern as
    `analyze(program, source_path=str(src), emit_indexes=False)` →
    `AnalysisResult`. `AnalysisResult.diagnostics` is the diagnostic list
    (voss/diagnostics.py:40-51; `.warnings`/`.errors` filter by severity).

Diagnostic / Span — voss/diagnostics.py:13-18 (live)
  - `@dataclass(frozen=True, slots=True) class Diagnostic: severity:
    DiagnosticSeverity ("warning"|"error"); code: str; message: str; span:
    Span; hint: str | None = None`
  - `Span` exposes `.file: str`, `.line_start: int`, `.col_start: int` (also
    `line_end/col_end/synthetic` — OMITTED from the frozen schema).

Test seam — tests/skills/conftest.py (created by T7-01, DO NOT modify)
  - Autouse `isolated_state` (XDG sandbox), `git_repo` fixture +
    `seed_git_repo(root) -> Path` helper, module-level `FakeProvider`.
    Deterministic skills do NOT need `FakeProvider` — they take
    `provider=None`. `make_toolset`, `PermissionGate`, `PlainRenderer`,
    `Plan` are re-exported from conftest (T7-01 Task 1).
  - `tests/skills/test_skills_smoke.py` (created by T7-01) holds 7 stubs
    whose bodies are `pytest.fail("not yet")`. T7-02 replaces ONLY the
    bodies of `test_rename_symbol` and `test_voss_lint`. It does NOT touch
    `test_add_test`, `test_summarize_diff`, `test_port_py_to_voss`,
    `test_audit_cognition` (owned by T7-03/T7-04) or `test_registry_count`
    (see registry-count contract below).
  - Fixtures landed by T7-01: `tests/skills/fixtures/rename-symbol/foo.py`
    (`def foo():` returning a constant) + `caller.py`
    (`from foo import foo` then a `foo()` call);
    `tests/skills/fixtures/voss-lint/bad.voss` (one stable seeded analyzer
    violation, e.g. reference to an undefined variable inside an `fn`).

registry-count contract (T7-01-PLAN lines 138-143, 233-234) — READ CAREFULLY
  - T7-01 specifies `test_registry_count` asserts the FINAL count of 7
    (`analyze` + 6) and is the last-to-green guard. After T7-02 the registry
    has only 3 entries (`analyze` + `rename-symbol` + `voss-lint-as-skill`),
    so a `== 7` assertion CANNOT pass until T7-04 registers the last skills.
  - T7-02 MUST NOT weaken `test_registry_count` (e.g. to `== 3` or `>= 3`) —
    that would silently degrade a final-count assertion the scope brief
    explicitly forbids weakening. Leave `test_registry_count`'s body exactly
    as T7-01 stubbed it (or as a `== 7` assertion if T7-01 already wrote the
    real assertion). It legitimately stays RED through T7-02 and T7-03 and
    goes green only at T7-04. T7-02 instead proves its OWN registrations via
    a direct registry check inside `test_rename_symbol`/`test_voss_lint` and
    in `<verify>`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement SKL-06 voss-lint-as-skill (deterministic, read-only, frozen M11 JSON schema)</name>
  <read_first>
    voss/harness/skills/voss_lint_as_skill.py (file being created — confirm it does not exist yet)
    voss/harness/skills/analyze.py (module shape, imports, run() signature to mirror)
    voss/harness/skill_registry.py (the registration site — context only, edited in Task 3)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 301-405 — voss_lint_as_skill core pattern + frozen schema + landmine)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (lines 536-578 — Diagnostic fields + field mapping; lines 661-674 — SKL-06 notes; Pitfall 7 lines 748-750)
    tests/skills/fixtures/voss-lint/bad.voss (the seeded fixture from T7-01 — confirm the violation it contains)
  </read_first>
  <action>
    Create `voss/harness/skills/voss_lint_as_skill.py`. Module header
    docstring states: deterministic, read-only, ZERO provider calls
    (D-08/D-10); emits the FROZEN M11 diagnostics schema (D-12) — schema is a
    contract, do not change field names once written.

    Imports: `from __future__ import annotations`, `import json`,
    `from pathlib import Path`, `import click`, `from voss.parser import
    parse`, `from voss.analyzer import analyze`, `from voss.diagnostics
    import Diagnostic`. Do NOT import `voss.cli._parse_file` or
    `voss.cli._walk_voss_sources` — those are private CLI helpers (RESEARCH
    Pitfall 7 / landmine). Walk files inline with `Path.rglob("*.voss")`.

    Define `def run(*, cwd: Path, provider, history, record, renderer, tools,
    gate, args: list[str] | None = None) -> None:`. `provider`, `history`,
    `record`, `tools`, `gate` are accepted for signature parity but the
    deterministic path MUST NOT call `provider`, `run_turn`, or any tool —
    enforce determinism by construction (no `asyncio.run`, no `tools[...]`).

    Resolve the target: `target = Path(args[0]) if args else cwd`; if `not
    target.is_absolute()`, set `target = cwd / target`. If `target` is a file
    ending `.voss`, the source list is `[target]`; otherwise it is
    `sorted(target.rglob("*.voss"))`.

    For each `.voss` source: read text, `program = parse(source,
    file=str(p))`, `result = analyze(program, source_path=str(p),
    emit_indexes=False)`, extend an `all_diags: list[Diagnostic]` with
    `result.diagnostics`. Wrap per-file parse/analyze in `try/except
    Exception as exc` and on failure append a synthetic finding for that file
    (severity `"error"`, rule `"PARSE"`, line 1, col 1, msg = `str(exc)`,
    hint `None`) so a malformed file does not abort the whole run.

    Build the FROZEN schema dict EXACTLY: top-level keys `version` (int
    literal `1`) and `findings` (list). Each finding object has EXACTLY these
    keys in this order: `file` (from `d.span.file`), `line`
    (`d.span.line_start`), `col` (`d.span.col_start`), `rule` (`d.code`),
    `severity` (`d.severity`), `msg` (`d.message`), `hint` (`d.hint`, may be
    `None` → serialized as JSON `null`). Omit `line_end`, `col_end`,
    `synthetic` (no M11 value — RESEARCH line 576). Emit with
    `click.echo(json.dumps(schema, indent=2))` to stdout (NOT via `renderer`
    — renderer is for human-readable streaming; this is structured machine
    output, D-12 M11 contract).

    NO `.voss` companion file for this skill (D-06 — deterministic skill, the
    language adds nothing). Do NOT register it here (Task 3 owns the
    registry).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "import ast; ast.parse(open('voss/harness/skills/voss_lint_as_skill.py').read()); print('ast ok')" && grep -q "from voss.parser import parse" voss/harness/skills/voss_lint_as_skill.py && grep -q "from voss.analyzer import analyze" voss/harness/skills/voss_lint_as_skill.py && python -c "import re,sys; s=open('voss/harness/skills/voss_lint_as_skill.py').read(); body='\n'.join(l for l in s.splitlines() if not l.lstrip().startswith('#')); assert not re.search(r'_parse_file|_walk_voss_sources|run_turn|asyncio', body), 'forbidden import/usage'; print('no-private-helper ok')"</automated>
  </verify>
  <done>`voss/harness/skills/voss_lint_as_skill.py` parses, imports the public `voss.parser.parse` + `voss.analyzer.analyze`, contains no private CLI helper imports and no provider/run_turn/asyncio usage in code (comments excluded). `run()` has the deterministic kwargs signature incl. `args`. Schema emission is exercised end-to-end by `test_voss_lint` in Task 3.</done>
</task>

<task type="auto">
  <name>Task 2: Implement SKL-01 rename-symbol (deterministic, mutating, gate-enforced)</name>
  <read_first>
    voss/harness/skills/rename_symbol.py (file being created — confirm it does not exist yet)
    voss/harness/skills/voss_lint_as_skill.py (Task 1 output — mirror its deterministic module shape + run() signature)
    voss/harness/skills/analyze.py (run() signature + click.echo output convention)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 236-298 — rename_symbol core pattern; lines 697-718 — shared gate-check pattern)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (lines 601-619 — SKL-01 scoping-engine recommendation; lines 719-723 — Pitfall 2 gate bypass; landmine #3 lines 486-499)
    voss/harness/tools.py (lines 20-50 ToolEntry.invoke; lines 360-375 fs_grep/fs_read/fs_edit entries — confirm invoke kwargs)
    tests/skills/fixtures/rename-symbol/foo.py and caller.py (the seeded fixture from T7-01)
  </read_first>
  <action>
    Create `voss/harness/skills/rename_symbol.py`. Module header docstring
    states: deterministic (D-08, ZERO provider calls), mutating (D-09 —
    `mutating=True`), writes ONLY through the gated `fs_edit` tool, and
    self-enforces the permission gate because it runs OUTSIDE `run_turn`
    (RESEARCH landmine #3 / Pitfall 2). Confirm and adopt the RESEARCH
    discretion call: anchor + `fs_grep`/`fs_edit` heuristic scoping engine
    (NOT Python `ast` — RESEARCH line 605 verified zero `ast` usage in the
    codebase; AST cross-file resolution is unwarranted complexity for this
    skill).

    Imports: `from __future__ import annotations`, `import asyncio`,
    `from pathlib import Path`, `import click`. Define `def run(*, cwd: Path,
    provider, history, record, renderer, tools, gate, args: list[str] | None
    = None) -> None:`. `provider`/`history`/`record` accepted for parity,
    never used (determinism by construction — no `run_turn`).

    Argument validation: if `args is None or len(args) < 2`, emit
    `click.echo("usage: rename-symbol <old> <new>", err=True)` and `return`.
    Bind `old, new = args[0], args[1]`.

    Discovery (read-only — `fs_grep` is_mutating=False, NO gate.check needed):
    `hits = asyncio.run(tools["fs_grep"].invoke(pattern=rf"\b{old}\b",
    glob="**/*.py"))`. Parse the grep result into a deduplicated set of file
    paths (relative to `cwd`). If no hits, emit a "no occurrences of <old>
    found" message and `return` (zero mutations, exit cleanly).

    Mutation loop — gate-enforced. For each file path: BEFORE invoking
    `fs_edit`, call `allowed, reason = gate.check("fs_edit", {"path":
    <path>, "old": old, "new": new}, is_mutating=True)`. If `not allowed`:
    emit `click.echo(f"rename-symbol: {reason}", err=True)` and `return`
    IMMEDIATELY — do not continue to other files, do not retry, do not
    escalate, do not fall back to a direct write. This is the `plan`-mode
    clean-refusal path (D-09/D-11, T5 D-12 precedent): in `plan` mode the
    FIRST `gate.check` returns `(False, "denied by mode plan")` and the skill
    must exit having mutated nothing. Only when `allowed` is true,
    `asyncio.run(tools["fs_edit"].invoke(path=<path>, old=<old_text>,
    new=<new_text>))`. Use a word-boundary-safe replacement so `old` is
    renamed to `new` for whole-token occurrences only (mirror the
    `\b<old>\b` anchor used in discovery; `fs_edit` enforces unique-match per
    its own contract — read each file via `tools["fs_read"]` if needed to
    construct unambiguous old/new edit context). Never call `Path.write_text`
    / `open(...,'w')` / `shell_run` directly — all mutation flows through
    `fs_edit` so the gate (already checked) and the cwd jail in `fs_edit`
    apply (RESEARCH Security Domain — path-traversal mitigated by `fs_edit`'s
    `jail_path`).

    Output is human-readable text via `click.echo` (D-12 — the meaningful
    effect is the file mutation itself; no JSON). Summarize files changed.

    NO `.voss` companion (D-06). Do NOT register here (Task 3).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "import ast; ast.parse(open('voss/harness/skills/rename_symbol.py').read()); print('ast ok')" && python -c "import re; s=open('voss/harness/skills/rename_symbol.py').read(); body='\n'.join(l for l in s.splitlines() if not l.lstrip().startswith('#')); assert not re.search(r'run_turn|provider\.|\.write_text\(|open\([^)]*[\x27\x22]w|shell_run', body), 'forbidden mutation/provider path'; assert re.search(r'gate\.check\(\s*[\x27\x22]fs_edit', body), 'missing explicit gate.check before fs_edit'; print('gate-enforced deterministic ok')"</automated>
  </verify>
  <done>`voss/harness/skills/rename_symbol.py` parses; contains no `run_turn`/`provider.`/direct-write/`shell_run` usage in code; calls `gate.check("fs_edit", ..., is_mutating=True)` before mutating. Behavioural plan-refusal + edit-rename assertions are exercised end-to-end by `test_rename_symbol` in Task 3.</done>
</task>

<task type="auto">
  <name>Task 3: Register both skills + turn test_rename_symbol & test_voss_lint green</name>
  <read_first>
    voss/harness/skill_registry.py (the full live file — the `analyze` registration block lines 35-59 is the exact template)
    voss/harness/skills/rename_symbol.py (Task 2 output — confirm run() kwargs incl. args)
    voss/harness/skills/voss_lint_as_skill.py (Task 1 output — confirm run() kwargs incl. args)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 34-114 — registration pattern + the 6-row id/module/mutating table)
    tests/skills/test_skills_smoke.py (T7-01 output — the 7 stubs; replace ONLY test_rename_symbol + test_voss_lint bodies)
    tests/skills/conftest.py (T7-01 output — re-exported helpers; deterministic skills need no FakeProvider)
    .planning/phases/T7-skills-bootstrap/T7-01-test-scaffold-PLAN.md (lines 138-143, 233-234 — registry-count contract: do NOT weaken test_registry_count)
  </read_first>
  <action>
    Edit `voss/harness/skill_registry.py`. Inside `default_skill_registry()`,
    AFTER the existing `analyze` `registry.register(...)` block and BEFORE
    `return registry`, add TWO registrations mirroring the `analyze` template
    exactly (inner function unpacking `ctx`, then `registry.register(...)`):

    (1) `def rename_symbol(ctx: Any, args: list[str]) -> None:` →
    `from .skills.rename_symbol import run` then call `run(cwd=ctx.cwd,
    provider=ctx.provider, history=ctx.history, record=ctx.record,
    renderer=ctx.renderer, tools=ctx.tools, gate=ctx.gate, args=args)`.
    Register `SkillEntry(id="rename-symbol", description="Anchor + scope-aware
    rename across the repo.", handler=rename_symbol, mutating=True)`.

    (2) `def voss_lint_as_skill(ctx: Any, args: list[str]) -> None:` →
    `from .skills.voss_lint_as_skill import run` then call `run(...)` with the
    same kwargs incl. `args=args`. Register `SkillEntry(
    id="voss-lint-as-skill", description="Lint .voss sources and emit
    structured JSON diagnostics.", handler=voss_lint_as_skill,
    mutating=False)`.

    Note the hyphenated `id` vs underscored module name (RESEARCH Pitfall 1):
    `id="rename-symbol"` imports `from .skills.rename_symbol import run`;
    `id="voss-lint-as-skill"` imports `from .skills.voss_lint_as_skill import
    run`. Keep edits additive and the block ordering stable so T7-03/T7-04
    can append two more registrations each without conflict (downstream
    consumer constraint).

    Edit `tests/skills/test_skills_smoke.py`: replace ONLY the bodies of
    `test_rename_symbol` and `test_voss_lint` (the T7-01 `pytest.fail("not
    yet")` stubs). Do NOT modify `test_add_test`, `test_summarize_diff`,
    `test_port_py_to_voss`, `test_audit_cognition` (owned by T7-03/T7-04) or
    `test_registry_count`. CRITICAL: leave `test_registry_count` exactly as
    T7-01 left it — it asserts the FINAL count of 7 and legitimately stays
    RED until T7-04 (T7-01-PLAN lines 138-143/233-234). Do NOT weaken it to
    `== 3`/`>= 3` — silently degrading a final-count assertion is forbidden
    by the scope contract. (Add a one-line module/comment note that
    `test_registry_count` is the last-to-green guard, owned by T7-04.)

    `test_voss_lint` body: copy `tests/skills/fixtures/voss-lint/bad.voss`
    into a `tmp_path` working dir; import `run` from
    `voss.harness.skills.voss_lint_as_skill`; capture stdout (patch
    `click.echo` into a buffer, per T7-PATTERNS lines 643-662); call `run`
    with `provider=None`, `record=types.SimpleNamespace(model="fake",
    id="t")`, `renderer=PlainRenderer()`, `tools=make_toolset(tmp_path)`,
    `gate=PermissionGate(auto_yes=True)`, `args=[str(tmp_path)]`;
    `json.loads` the output; assert `schema["version"] == 1`,
    `isinstance(schema["findings"], list)`, the seeded violation is present
    (at least one finding whose `rule`/`severity`/`msg` matches the known
    `bad.voss` violation), and every finding has exactly keys
    `{file,line,col,rule,severity,msg,hint}`. Also assert
    `default_skill_registry().get("voss-lint-as-skill")` returns an entry
    with `mutating is False` (proves Task 3's registration WITHOUT touching
    `test_registry_count`).

    `test_rename_symbol` body: copy the
    `tests/skills/fixtures/rename-symbol/` `*.py` files into a `tmp_path`
    dir; import `run` from `voss.harness.skills.rename_symbol`. (a) Run with
    `gate=PermissionGate(mode="plan")`, `args=["foo","bar"]` and assert the
    `.py` files are byte-identical before/after (clean refusal, no
    escalation — D-09/D-11). (b) Run with `gate=PermissionGate(auto_yes=
    True)`, `args=["foo","bar"]` and assert `foo` is renamed to `bar` across
    both files (`"foo" not in joined_source and "bar" in joined_source`).
    Also assert `default_skill_registry().get("rename-symbol")` is an entry
    with `mutating is True`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "from voss.harness.skill_registry import default_skill_registry as d; r=d(); ids=r.ids(); assert {'analyze','rename-symbol','voss-lint-as-skill'} <= set(ids), ids; assert r.get('rename-symbol').mutating is True; assert r.get('voss-lint-as-skill').mutating is False; print('registry ok', ids)" && test "$(grep -c 'SkillEntry(' voss/harness/skill_registry.py)" -eq 3 && pytest tests/skills/test_skills_smoke.py::test_rename_symbol tests/skills/test_skills_smoke.py::test_voss_lint -q && python -c "import subprocess,sys; r=subprocess.run([sys.executable,'-m','pytest','tests/skills/test_skills_smoke.py::test_registry_count','-q'],capture_output=True); sys.exit(0 if r.returncode!=0 else 1)" && echo "EXPECTED: test_registry_count still RED until T7-04 (final-count guard not weakened)"</automated>
  </verify>
  <done>`default_skill_registry()` exposes `rename-symbol` (mutating=True) + `voss-lint-as-skill` (mutating=False) + `analyze`; exactly 3 `SkillEntry(` literals in the registry file (additive, no T7-03/04 collision). `test_rename_symbol` and `test_voss_lint` pass green. `test_registry_count` is still RED (asserts the final 7; NOT weakened — goes green only at T7-04). `test_add_test`/`test_summarize_diff`/`test_port_py_to_voss`/`test_audit_cognition` remain untouched stubs.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| skill invocation → filesystem (rename-symbol) | `rename-symbol` is deterministic + mutating and runs OUTSIDE `run_turn`, so the agent loop's automatic gate enforcement does NOT apply — the gate must be self-enforced before every write |
| permission mode (`plan`) → mutating skill | `plan` mode must structurally prevent any mutation by `rename-symbol`; no escalation, no bypass, no direct-write fallback |
| `.voss` source under target path → SKL-06 parser/analyzer | Untrusted/arbitrary `.voss` files are parsed; a malformed file must not crash the whole lint run |
| skill output → M11 consumer (SKL-06 JSON) | The JSON schema is a frozen downstream contract; field drift is a correctness/compatibility hazard |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T7-02-01 | Elevation of Privilege | `rename_symbol.run` deterministic mutation path | mitigate | Task 2 requires an explicit `gate.check("fs_edit", {...}, is_mutating=True)` before EVERY `fs_edit` invoke; `not allowed` → immediate `return` with no retry/escalation/direct-write. Task 2 verify greps that `gate.check("fs_edit"...)` is present and that no `.write_text`/`open(...,'w')`/`shell_run` exists. Task 3's `test_rename_symbol` asserts `plan` mode mutates ZERO bytes. (RESEARCH landmine #3 / Pitfall 2; block-on-high invariant.) |
| T-T7-02-02 | Tampering | `plan`-mode write path | mitigate | First `gate.check` in `plan` mode returns `(False, "denied by mode plan")`; skill exits having mutated nothing. `test_rename_symbol` case (a) byte-compares the fixture files before/after under `PermissionGate(mode="plan")` — a structural test that the bypass cannot pass silently. |
| T-T7-02-03 | Tampering | SKL-01 path traversal via `fs_edit` | accept | All mutation flows through the gated `fs_edit` tool whose `jail_path` confines writes to `cwd` (RESEARCH Security Domain). The skill never constructs raw filesystem paths or calls `Path.write_text`; Task 2 verify forbids direct writes. No additional control needed. |
| T-T7-02-04 | Denial of Service | SKL-06 parsing a malformed `.voss` file | mitigate | Task 1 requires per-file `try/except Exception` that converts a parse/analyze failure into a synthetic `PARSE` error finding instead of aborting the run, so one bad file cannot DoS the lint of a tree. |
| T-T7-02-05 | Information Disclosure | SKL-06 JSON schema drift | mitigate | Schema field set is FROZEN and enumerated exactly in Task 1 (`{version, findings:[{file,line,col,rule,severity,msg,hint}]}`); Task 3's `test_voss_lint` asserts each finding has EXACTLY those 7 keys, preventing silent field addition/removal that would break M11 consumers. |
| T-T7-02-SC | Tampering | npm/pip/cargo installs | mitigate | T7 introduces ZERO new packages (RESEARCH §"Package Legitimacy Audit": all deps are existing stdlib/project modules — `voss.parser`, `voss.analyzer`, `voss.diagnostics`, `click`, stdlib `json`/`asyncio`/`pathlib`). No install task in this plan → no slopcheck / legitimacy checkpoint required. |

Block-on-high: T-T7-02-01 / T-T7-02-02 (skill bypasses the central permission
gate). These are structurally prevented by Task 2's explicit `gate.check`
requirement and asserted by Task 3's `plan`-mode byte-comparison test. No new
dependencies, no network surface.
</threat_model>

<verification>
Phase-level checks for this plan (run after all 3 tasks):

```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. Both handler modules parse and have the deterministic run() signature
python -c "import ast; [ast.parse(open(f).read()) for f in ('voss/harness/skills/rename_symbol.py','voss/harness/skills/voss_lint_as_skill.py')]"

# 2. Determinism invariant — zero provider/run_turn coupling (comments excluded)
python -c "import re; [exec('s=open(f).read(); b=chr(10).join(l for l in s.splitlines() if not l.lstrip().startswith(chr(35))); assert not re.search(r\"run_turn|provider\\.\", b), f') for f in ('voss/harness/skills/rename_symbol.py','voss/harness/skills/voss_lint_as_skill.py')]"

# 3. SKL-01 self-enforces the gate; no direct-write/shell bypass
grep -qE 'gate\.check\(\s*["\x27]fs_edit' voss/harness/skills/rename_symbol.py
! grep -qE '\.write_text\(|shell_run|run_turn' voss/harness/skills/rename_symbol.py

# 4. SKL-06 uses public parser/analyzer, no private cli helpers
grep -q 'from voss.parser import parse' voss/harness/skills/voss_lint_as_skill.py
grep -q 'from voss.analyzer import analyze' voss/harness/skills/voss_lint_as_skill.py
! grep -qE '_parse_file|_walk_voss_sources' voss/harness/skills/voss_lint_as_skill.py

# 5. Registry: 3 entries, correct mutating flags, additive (T7-03/04 can append)
python -c "from voss.harness.skill_registry import default_skill_registry as d; r=d(); assert {'analyze','rename-symbol','voss-lint-as-skill'}<=set(r.ids()); assert r.get('rename-symbol').mutating is True; assert r.get('voss-lint-as-skill').mutating is False"
test "$(grep -c 'SkillEntry(' voss/harness/skill_registry.py)" -eq 3

# 6. The two owned tests are green; the others (incl. registry_count) are untouched/RED
pytest tests/skills/test_skills_smoke.py::test_rename_symbol tests/skills/test_skills_smoke.py::test_voss_lint -q
pytest tests/skills/test_skills_smoke.py::test_registry_count -q || echo "OK: registry_count still RED (final-count guard, T7-04 turns it green)"

# 7. No .voss companion was created (D-06 — deterministic skills are Python-only)
test ! -e voss/harness/skills/voss/rename-symbol.voss
test ! -e voss/harness/skills/voss/voss-lint-as-skill.voss

# 8. No whitespace damage
git diff --check
```
</verification>

<success_criteria>
- `voss/harness/skills/rename_symbol.py` and `voss/harness/skills/voss_lint_as_skill.py` exist, parse, and define `run(*, cwd, provider, history, record, renderer, tools, gate, args=None)`.
- SKL-01 `rename-symbol`: in `plan` mode it mutates ZERO bytes and refuses cleanly (no escalation/bypass); in `edit`/`auto` it renames `foo`→`bar` across all `*.py` files via the gated `fs_edit` tool, with an explicit `gate.check("fs_edit", ..., is_mutating=True)` before every mutating invoke. No `run_turn`/`provider`/direct-write/`shell_run` usage.
- SKL-06 `voss-lint-as-skill`: zero provider calls; uses public `voss.parser.parse` + `voss.analyzer.analyze` (no private CLI helpers); emits one JSON object `{version: 1, findings: [{file,line,col,rule,severity,msg,hint}]}` to stdout; finds the seeded `bad.voss` violation.
- `default_skill_registry()` registers `rename-symbol` (mutating=True) and `voss-lint-as-skill` (mutating=False) alongside `analyze`; exactly 3 `SkillEntry(` literals; edits are additive so T7-03/T7-04 append without conflict.
- `tests/skills/test_skills_smoke.py::test_rename_symbol` and `::test_voss_lint` pass green.
- `test_registry_count` is NOT weakened — it still asserts the final count of 7 and remains RED until T7-04; `test_add_test`/`test_summarize_diff`/`test_port_py_to_voss`/`test_audit_cognition` remain untouched stubs.
- No `.voss` companion files created for these two skills (D-06).
- `git diff --check` is clean.
</success_criteria>

<output>
Create `.planning/phases/T7-skills-bootstrap/T7-02-SUMMARY.md` when done.
</output>
