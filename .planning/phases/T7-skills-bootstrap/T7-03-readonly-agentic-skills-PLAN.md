---
phase: T7-skills-bootstrap
plan: 03
type: execute
wave: 3
depends_on: [T7-01, T7-02]
files_modified:
  - voss/harness/skills/summarize_diff.py
  - voss/harness/skills/audit_cognition.py
  - voss/harness/skills/voss/summarize-diff.voss
  - voss/harness/skills/voss/audit-cognition.voss
  - voss/harness/skill_registry.py
  - tests/skills/test_skills_smoke.py
autonomous: true
requirements: [SKL-03, SKL-05]

must_haves:
  truths:
    - "Running `summarize-diff` drives an agent turn via run_turn that calls `git_diff` and prints structured markdown containing the stable section headers `## Title`, `## Summary`, `## Changes`"
    - "`summarize-diff` performs ZERO file mutations (read-only, mutating=False)"
    - "Running `audit-cognition` loads the cognition bundle, computes drift, drives a run_turn whose prompt forbids file writes, and emits a `PROPOSAL:` block"
    - "`audit-cognition` NEVER writes `architecture.md` / `VOSS.md` — both are byte-identical before and after the run (D-05/D-10/Pitfall 3)"
    - "`voss check voss/harness/skills/voss/summarize-diff.voss` exits 0"
    - "`voss check voss/harness/skills/voss/audit-cognition.voss` exits 0"
    - "`default_skill_registry()` registers `summarize-diff` (mutating=False) and `audit-cognition` (mutating=False) in addition to T7-02's `analyze` + `rename-symbol` + `voss-lint-as-skill`"
    - "`tests/skills/test_skills_smoke.py::test_summarize_diff` and `::test_audit_cognition` pass green under FakeProvider"
  artifacts:
    - path: "voss/harness/skills/summarize_diff.py"
      provides: "SKL-03 agentic read-only handler — run_turn via asyncio.run, prompt requires the 3 stable markdown sections"
      contains: "def run"
      min_lines: 25
    - path: "voss/harness/skills/audit_cognition.py"
      provides: "SKL-05 agentic read-only handler — cognition.load()+drift_check() preamble, write-forbidding prompt, never writes architecture.md"
      contains: "def run"
      min_lines: 35
    - path: "voss/harness/skills/voss/summarize-diff.voss"
      provides: "SKL-03 .voss companion (dogfood demo, voss-check-pass, NOT exec path)"
      contains: "fn summarizeDiff"
    - path: "voss/harness/skills/voss/audit-cognition.voss"
      provides: "SKL-05 .voss companion (dogfood demo, voss-check-pass, NOT exec path)"
      contains: "fn proposeCognitionUpdate"
    - path: "voss/harness/skill_registry.py"
      provides: "two new SkillEntry registrations (summarize-diff, audit-cognition) appended after T7-02's"
      contains: "summarize-diff"
    - path: "tests/skills/test_skills_smoke.py"
      provides: "test_summarize_diff + test_audit_cognition bodies turned green (test_registry_count stays RED until T7-04)"
      contains: "def test_summarize_diff"
  key_links:
    - from: "voss/harness/skill_registry.py"
      to: "voss.harness.skills.summarize_diff.run"
      via: "default_skill_registry() inner handler imports + calls run(...)"
      pattern: "from .skills.summarize_diff import run"
    - from: "voss/harness/skill_registry.py"
      to: "voss.harness.skills.audit_cognition.run"
      via: "default_skill_registry() inner handler imports + calls run(...)"
      pattern: "from .skills.audit_cognition import run"
    - from: "voss/harness/skills/summarize_diff.py"
      to: "voss.harness.agent.run_turn"
      via: "asyncio.run(run_turn(prompt, ...)) — agent calls git_diff tool"
      pattern: "from ..agent import run_turn"
    - from: "voss/harness/skills/audit_cognition.py"
      to: "voss.harness.cognition.load + drift_check"
      via: "pre-run_turn preamble: bundle = cognition.load(cwd); cognition.drift_check(cwd, fm)"
      pattern: "cognition\\.drift_check\\("
---

<objective>
Implement the two read-only agentic skills (D-07 agentic, D-10 read-only,
`mutating=False`): SKL-03 `summarize-diff` (agent runs `git diff`, emits a
PR-shaped markdown with the stable sections `## Title` / `## Summary` /
`## Changes` per D-12) and SKL-05 `audit-cognition` (loads cognition, computes
drift, drives a run_turn whose prompt forbids file writes and emits a
`PROPOSAL:` block — NEVER writes `architecture.md`/`VOSS.md`, D-05/D-10/Pitfall
3). Ship a `voss check`-passing `.voss` companion for each (D-05 dogfood
demonstration, NOT the runtime exec path). Register both in
`default_skill_registry()` and turn their two smoke tests green.

Purpose: These are the first `run_turn`/`FakeProvider`-exercising skills.
Both are read-only so the security invariant is a *non-mutation* invariant:
`audit-cognition` must emit a proposal and leave `architecture.md`/`VOSS.md`
byte-unchanged (Pitfall 3 — the LLM may otherwise "apply" its proposal). The
two `.voss` companions are the roadmap's "Python with a `.voss` lint pass
demonstrating composability" deliverable for these skills (D-05).

Output: `voss/harness/skills/summarize_diff.py`,
`voss/harness/skills/audit_cognition.py`, two `.voss` companions under
`voss/harness/skills/voss/`, two `SkillEntry` registrations appended in
`voss/harness/skill_registry.py`, and green bodies for `test_summarize_diff` +
`test_audit_cognition` in `tests/skills/test_skills_smoke.py`.
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
@.planning/phases/T7-skills-bootstrap/T7-02-deterministic-skills-PLAN.md

<interfaces>
<!-- Contracts the executor needs. Extracted from live source — no codebase exploration required. -->

Agentic handler template — voss/harness/skills/analyze.py (live, full file)
  - `from __future__ import annotations`, `import asyncio`, `import click`,
    `from pathlib import Path`, `from .. import cognition` (and `voss_md` —
    audit_cognition needs `cognition`; summarize_diff needs neither),
    `from ..agent import run_turn`.
  - `def run(*, cwd: Path, provider, history, record, renderer, tools, gate)
    -> None:` — EXACT keyword-only signature. Agentic skills do NOT take an
    `args` param (only the deterministic T7-02 skills added `args`); the
    registry inner handler for an agentic skill passes positionally-empty
    `_args` analog (see registration interface below).
  - The agentic call shape (analyze.py:55-68), copy verbatim, swap the prompt:
    `asyncio.run(run_turn(prompt, tools=tools, cwd=cwd, renderer=renderer,
    model=record.model, provider=provider, history=history, permissions=gate,
    cognition=None, session_id=record.id))`. `run()` stays a SYNC function —
    never add `async` to it; `asyncio.run` is the bridge (RESEARCH A3:
    slash/CLI call sites have no running loop).

run_turn signature — voss/harness/agent.py:412 (live)
  - `async def run_turn(task: str, *, tools, cwd, renderer,
    confidence_threshold=0.60, token_budget=60_000, model=None, provider=None,
    history=None, permissions=None, session_id=None, cognition=None,
    prior_context=None, voss_md_text=None) -> TurnResult`.

cognition API — voss/harness/cognition.py (live, signatures verified)
  - `def load(cwd: Path, *, token_count=None) -> CognitionBundle` (line 253).
    `class CognitionBundle: initialized: bool; ...;
    architecture_frontmatter: Optional[ArchitectureFrontmatter] = None`
    (lines 50-54). When `_is_initialized(cwd)` is False, `load` returns
    `CognitionBundle(initialized=False)` (line 255-256) with
    `architecture_frontmatter=None`.
  - `def drift_check(cwd: Path, fm: ArchitectureFrontmatter) -> DriftStatus`
    (line 278). `class DriftStatus: is_stale: bool; head_diverged_by: int;
    file_count_delta: int; days_elapsed: int; reason: str = ""`
    (lines 63-68).
  - Import as `from .. import cognition`; reference `cognition.load`,
    `cognition.drift_check`, `cognition.DriftStatus`. (Same import style
    `analyze.py:18` uses.)

SkillEntry / default_skill_registry — voss/harness/skill_registry.py (live)
  - `@dataclass(frozen=True) class SkillEntry: id: str; description: str;
    handler: SkillHandler; mutating: bool = False`.
  - `SkillHandler = Callable[[Any, list[str]], None]` — handler is
    `(ctx: Any, args: list[str]) -> None`. The existing `analyze` inner
    handler is `def analyze(ctx: Any, _args: list[str]) -> None:` (it ignores
    args). Agentic skills follow the `analyze` shape: name the second param
    `_args` and do NOT forward it (these skills take no positional CLI args).
  - AFTER T7-02 the body of `default_skill_registry()` contains, in order:
    the `analyze` inner+`register`, then `rename_symbol` inner+`register`,
    then `voss_lint_as_skill` inner+`register`, then `return registry`
    (3 `SkillEntry(` literals total). T7-03 inserts TWO more inner+`register`
    blocks BETWEEN the `voss_lint_as_skill` registration and `return registry`
    — strictly additive, preserving T7-02's block order so T7-04 can append
    its final two cleanly (downstream-consumer constraint). After T7-03 there
    are exactly 5 `SkillEntry(` literals.

Test seam — tests/skills/conftest.py (created by T7-01, DO NOT modify)
  - Autouse `isolated_state` (XDG sandbox per test). Module-level
    `FakeProvider` (copied verbatim from
    `tests/harness/test_agent_integration.py:30-102`): construct as
    `FakeProvider(plan)` where `plan` is a `Plan`; its `stream()` emits the
    canned plan on call 0 and a synthetic done plan after — `run_turn` drives
    `provider.stream()` (Pitfall 4). `Plan`, `ToolCall`, `PermissionGate`,
    `PlainRenderer`, `make_toolset` are re-exported from conftest (T7-01
    Task 1) — import them from `tests.skills.conftest`.
  - `git_repo` fixture + `seed_git_repo(root) -> Path` helper: builds a temp
    git tree (git init + config + README + initial commit), returns the root.
  - Fixtures landed by T7-01:
    `tests/skills/fixtures/summarize-diff/README.md` (lets a test introduce
    an unstaged modification before invoking the skill);
    `tests/skills/fixtures/audit-cognition/.voss/architecture.md` (a
    pre-initialized cognition file with realistic frontmatter `git_head`,
    `analyzed_at`, `file_count`, `analyzer_version` + a short `# Architecture`
    body, so `cognition.load()` returns `initialized=True` with a non-None
    `architecture_frontmatter` and `drift_check` can run).

Smoke-test contract — tests/skills/test_skills_smoke.py (T7-01 created, T7-02 edited)
  - Holds 7 functions. T7-01 stubbed all as `pytest.fail("not yet")`; T7-02
    turned `test_rename_symbol` + `test_voss_lint` green and left
    `test_registry_count` asserting the FINAL count of 7 (RED until T7-04).
  - T7-03 replaces ONLY the bodies of `test_summarize_diff` and
    `test_audit_cognition`. It MUST NOT touch `test_rename_symbol`,
    `test_voss_lint` (T7-02, green — leave green), `test_add_test`,
    `test_port_py_to_voss` (T7-04 stubs — leave as `pytest.fail`), or
    `test_registry_count`.
  - CRITICAL (T7-01-PLAN lines 138-143/233-234, reaffirmed by T7-02-PLAN
    lines 167-179): `test_registry_count` asserts the final 7-entry count and
    is the last-to-green guard owned by T7-04. After T7-03 the registry has
    exactly 5 entries (`analyze`, `rename-symbol`, `voss-lint-as-skill`,
    `summarize-diff`, `audit-cognition`), so a `== 7` assertion legitimately
    stays RED. Do NOT weaken it to `== 5`/`>= 5` — silently degrading a
    final-count assertion is forbidden by the scope contract. Prove T7-03's
    OWN registrations via a direct `default_skill_registry()` check inside
    `test_summarize_diff`/`test_audit_cognition` and in `<verify>`.

.voss companion constructs — verified to pass `voss check` this planning run
  - The shape `fn NAME(arg: string) -> string { ctx(budget: N tokens) {
    yield ask("...") } }` parses and `voss check`-passes (probed against
    `python3 -m voss.cli check` during planning; matches the
    `samples/research.voss` agent-body / `voss/harness/agent/loop.voss:14`
    `ctx(budget: N tokens)` precedent). Use this exact shape — it is the
    simplest construct that `voss check`-passes for both companions
    (RESEARCH Pitfall 5: fall back to `fn` + `ctx(budget)` + `yield ask()` if
    a richer shape fails). String concatenation with `+` and a `string`
    parameter is valid (`samples/classify.voss:4`, `samples/support.voss:25`).
  - The `voss/harness/skills/voss/` directory already exists (T7-01 created it
    with a `.gitkeep`); the CI `voss check voss/harness/skills/voss/` step is
    already wired (T7-01 Task 3) — adding `.voss` files there is sufficient,
    no CI edit needed in this plan.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement SKL-03 summarize-diff handler + companion .voss</name>
  <read_first>
    voss/harness/skills/summarize_diff.py (file being created — confirm it does not exist)
    voss/harness/skills/analyze.py (lines 10-19 imports; lines 25-68 — the exact run() signature + asyncio.run(run_turn(...)) call shape to copy, swapping only the prompt)
    voss/harness/skills/voss/summarize-diff.voss (file being created — confirm it does not exist; the dir + .gitkeep already exist from T7-01)
    samples/classify.voss (string param + string concat reference) and samples/research.voss (lines 10-18 — ctx(budget: N tokens) { yield ask(...) } reference)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 118-194 — agentic skill module shape + per-skill prompt notes; lines 445-455 — summarize-diff.voss target shape)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (lines 631-640 — SKL-03 notes; lines 754-775 — FakeProvider/Plan steps with ToolCall(name="git_diff"))
  </read_first>
  <action>
    Create `voss/harness/skills/summarize_diff.py`. Module header docstring
    states: SKL-03, agentic (D-07 — invokes a model turn via `run_turn`),
    read-only (D-10 — `mutating=False`, NO file writes; the meaningful effect
    is the printed markdown). Output convention per D-12: structured markdown
    with the STABLE section headers `## Title`, `## Summary`, `## Changes`
    (PR-ready); these three header strings are a contract.

    Imports: `from __future__ import annotations`, `import asyncio`,
    `from pathlib import Path`, `from ..agent import run_turn`. (No
    `cognition`/`voss_md` needed for this skill — only `audit_cognition`
    needs `cognition`.)

    Define `def run(*, cwd: Path, provider, history, record, renderer, tools,
    gate) -> None:` — the EXACT keyword-only signature from
    `analyze.py:25-34` (no `args` param: agentic skills follow the `analyze`
    shape, not the deterministic-skill `args` extension). Keep `run` SYNC.

    Build a single `prompt` string instructing the agent to (a) obtain the
    current working-tree diff by calling the `git_diff` tool, and (b) write a
    pull-request description as its final answer, output ONLY structured
    markdown with EXACTLY the sections `## Title`, `## Summary`, and
    `## Changes` (name the three headers verbatim in the prompt so the model
    emits them). Explicitly instruct: do not write or modify any file; the
    response is the deliverable.

    Drive the agent with the `analyze.py:55-68` call shape verbatim, swapping
    only the prompt: `asyncio.run(run_turn(prompt, tools=tools, cwd=cwd,
    renderer=renderer, model=record.model, provider=provider,
    history=history, permissions=gate, cognition=None,
    session_id=record.id))`. Do NOT post-process, do NOT call any `fs_write`/
    `fs_edit`, do NOT touch `voss_md` — the agent's final markdown is
    surfaced through the renderer by `run_turn` itself (matching how
    `analyze.py` lets the turn render). The skill returns `None`
    (SkillHandler contract).

    Create the companion `voss/harness/skills/voss/summarize-diff.voss`. This
    is a dogfood demonstration of composability (D-05) and is NOT the runtime
    exec path. Use the verified-passing shape: a `# summarize-diff.voss`
    comment header, then `fn summarizeDiff(diff: string) -> string {` with a
    body `ctx(budget: 3000 tokens) { yield ask("...") }` where the `ask`
    string instructs summarizing the diff into a PR description with the
    `## Title` / `## Summary` / `## Changes` sections (use `+ diff` string
    concatenation to reference the param, mirroring
    `samples/classify.voss:4`). It must `voss check`-pass (Task 1 verify runs
    it). Do NOT register the skill here (Task 3 owns the registry edit).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "import ast; ast.parse(open('voss/harness/skills/summarize_diff.py').read()); print('ast ok')" && grep -q "from ..agent import run_turn" voss/harness/skills/summarize_diff.py && python3 -c "import re; s=open('voss/harness/skills/summarize_diff.py').read(); b=chr(10).join(l for l in s.splitlines() if not l.lstrip().startswith('#')); assert all(h in s for h in ('## Title','## Summary','## Changes')), 'missing stable section headers in prompt'; assert not re.search(r'fs_write|fs_edit|\.write_text\(|voss_md', b), 'read-only skill must not reference write paths'; print('summarize_diff ok')" && python3 -m voss.cli check voss/harness/skills/voss/summarize-diff.voss && echo "voss check summarize-diff.voss exit 0"</automated>
  </verify>
  <done>`voss/harness/skills/summarize_diff.py` parses, imports `run_turn`, names the three stable section headers in its prompt, references no write/`voss_md` path in code. `voss/harness/skills/voss/summarize-diff.voss` exists and `python3 -m voss.cli check` on it exits 0. Not yet registered (Task 3).</done>
</task>

<task type="auto">
  <name>Task 2: Implement SKL-05 audit-cognition handler (no-write) + companion .voss</name>
  <read_first>
    voss/harness/skills/audit_cognition.py (file being created — confirm it does not exist)
    voss/harness/skills/summarize_diff.py (Task 1 output — mirror its agentic module shape + run() signature)
    voss/harness/skills/analyze.py (lines 10-19 imports incl. `from .. import cognition`; lines 25-68 run()/run_turn call shape)
    voss/harness/cognition.py (lines 50-54 CognitionBundle; lines 63-68 DriftStatus; lines 253-269 load(); lines 278-296 drift_check() — confirm the exact field/return shapes)
    voss/harness/skills/voss/audit-cognition.voss (file being created — confirm it does not exist)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 196-232 — audit_cognition pre-run_turn preamble + DriftStatus; lines 491-503 — audit-cognition.voss target shape + validation requirement)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (lines 501-534 — cognition.* APIs + SKL-05 implementation sketch; lines 654-659 — SKL-05 notes; lines 725-729 — Pitfall 3 two-layer defense)
    tests/skills/fixtures/audit-cognition/.voss/architecture.md (T7-01 fixture — confirm the seeded frontmatter shape so the preamble's load() path is exercised)
  </read_first>
  <action>
    Create `voss/harness/skills/audit_cognition.py`. Module header docstring
    states: SKL-05, agentic (D-07), read-only (D-10 — `mutating=False`).
    HARD INVARIANT (D-05/D-10/Pitfall 3): this skill PROPOSES an
    `architecture.md` update and NEVER writes `architecture.md`/`VOSS.md` (or
    any file). A human / another flow applies the proposal.

    Imports: `from __future__ import annotations`, `import asyncio`,
    `from pathlib import Path`, `import click`, `from .. import cognition`,
    `from ..agent import run_turn`. Do NOT import `voss_md` and do NOT import
    any `fs_write`/`fs_edit` tool helper — the no-write invariant is enforced
    by construction (no write API is reachable from this module's code) AND
    by the prompt (defense layer 1, Pitfall 3) AND by Task 3's test asserting
    the file is byte-unchanged (defense layer 2).

    Define `def run(*, cwd: Path, provider, history, record, renderer, tools,
    gate) -> None:` — EXACT keyword-only signature from `analyze.py:25-34`
    (no `args`). Keep `run` SYNC.

    Pre-`run_turn` preamble (pure Python, before any `asyncio.run`), per
    T7-PATTERNS lines 196-221:
    - `bundle = cognition.load(cwd)`.
    - If `not bundle.initialized`: `click.echo("cognition not initialized —
      run /analyze first", err=True)` and `return` (no turn, no output).
    - If `bundle.architecture_frontmatter is None`: `click.echo("no
      architecture frontmatter — run /analyze first", err=True)` and
      `return`.
    - `drift = cognition.drift_check(cwd, bundle.architecture_frontmatter)`.
      `drift` is a `cognition.DriftStatus` with `.is_stale: bool` and
      `.reason: str` (default `""`).

    Build the `prompt` from the drift status. It MUST: state whether
    cognition is stale (`drift.is_stale`) and include `drift.reason` (use
    `"none"` when `reason` is empty); instruct the model to propose a
    ONE-PARAGRAPH update to the architecture description; and contain the
    explicit constraint, verbatim in spirit: "Do NOT write to any file.
    Output your proposal as a single paragraph starting with 'PROPOSAL:'."
    The literal token `PROPOSAL:` MUST appear in the prompt string (Task 3's
    test asserts the emitted final contains it; the FakeProvider's
    `final_when_done` will be set to a `PROPOSAL:`-prefixed string).

    Drive with the `analyze.py:55-68` call shape verbatim, swapping only the
    prompt: `asyncio.run(run_turn(prompt, tools=tools, cwd=cwd,
    renderer=renderer, model=record.model, provider=provider,
    history=history, permissions=gate, cognition=None,
    session_id=record.id))`. Do NOT pass a mutated/stripped toolset — the
    no-write guarantee comes from the prompt + the absence of any write call
    in this module + the test assertion, NOT from manual tool stripping
    (RESEARCH lines 656-659). After the turn, do NOT call `voss_md.*`, do NOT
    write any staging file, do NOT touch `architecture.md`/`VOSS.md`. Return
    `None`.

    Create the companion `voss/harness/skills/voss/audit-cognition.voss`
    (dogfood demo, D-05, NOT the exec path). Verified-passing shape: a
    `# audit-cognition.voss` comment header, then
    `fn proposeCognitionUpdate(drift: string) -> string {` with body
    `ctx(budget: 2000 tokens) { yield ask("...") }` where the `ask` string
    (using `+ drift` concatenation) instructs proposing a one-paragraph
    architecture.md update starting with `PROPOSAL:` and explicitly says do
    NOT write any file. Must `voss check`-pass (Task 2 verify runs it). Do
    NOT register here (Task 3).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "import ast; ast.parse(open('voss/harness/skills/audit_cognition.py').read()); print('ast ok')" && grep -q "from .. import cognition" voss/harness/skills/audit_cognition.py && grep -q "from ..agent import run_turn" voss/harness/skills/audit_cognition.py && python3 -c "import re; s=open('voss/harness/skills/audit_cognition.py').read(); b=chr(10).join(l for l in s.splitlines() if not l.lstrip().startswith('#')); assert 'cognition.load(' in b and 'cognition.drift_check(' in b, 'missing cognition preamble'; assert 'PROPOSAL:' in s, 'prompt must contain PROPOSAL: marker'; assert not re.search(r'fs_write|fs_edit|\.write_text\(|voss_md|architecture\.md|VOSS\.md', b), 'no-write invariant: must not reference any write/architecture path in code'; print('audit_cognition ok')" && python3 -m voss.cli check voss/harness/skills/voss/audit-cognition.voss && echo "voss check audit-cognition.voss exit 0"</automated>
  </verify>
  <done>`voss/harness/skills/audit_cognition.py` parses; has the `cognition.load()` + `drift_check()` preamble; its prompt contains the `PROPOSAL:` marker and forbids writes; code references no write API / `voss_md` / `architecture.md` / `VOSS.md`. `voss/harness/skills/voss/audit-cognition.voss` exists and `voss check` exits 0. Byte-unchanged assertion is exercised by `test_audit_cognition` in Task 3.</done>
</task>

<task type="auto">
  <name>Task 3: Register both skills + turn test_summarize_diff & test_audit_cognition green</name>
  <read_first>
    voss/harness/skill_registry.py (the full live file post-T7-02 — 3 SkillEntry blocks: analyze, rename_symbol, voss_lint_as_skill; the analyze block is the registration template)
    voss/harness/skills/summarize_diff.py (Task 1 output — confirm run() kwargs, no args param)
    voss/harness/skills/audit_cognition.py (Task 2 output — confirm run() kwargs, no args param)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 34-114 — registration pattern + the id/module/mutating table rows for summarize-diff & audit-cognition)
    tests/skills/test_skills_smoke.py (post-T7-02 — replace ONLY test_summarize_diff + test_audit_cognition bodies)
    tests/skills/conftest.py (T7-01 — FakeProvider + re-exported Plan/ToolCall/PermissionGate/PlainRenderer/make_toolset)
    tests/skills/fixtures/summarize-diff/README.md and tests/skills/fixtures/audit-cognition/.voss/architecture.md (T7-01 fixtures)
    .planning/phases/T7-skills-bootstrap/T7-01-test-scaffold-PLAN.md (lines 138-143, 233-234 — registry-count contract: do NOT weaken test_registry_count)
    .planning/phases/T7-skills-bootstrap/T7-02-deterministic-skills-PLAN.md (lines 167-179 — reaffirms the registry-count contract; lines 328-352 — additive registration ordering)
  </read_first>
  <action>
    Edit `voss/harness/skill_registry.py`. Inside `default_skill_registry()`,
    AFTER the existing `voss_lint_as_skill` `registry.register(...)` block
    (T7-02's last registration) and BEFORE `return registry`, append TWO
    registrations mirroring the `analyze` template exactly (inner function
    unpacking `ctx`, then `registry.register(...)`). Keep T7-02's three blocks
    untouched and in order; append strictly so T7-04 can append its final two
    after these without conflict (downstream-consumer constraint). Agentic
    skills take no positional args — name the inner param `_args` and do NOT
    forward it (mirror the existing `def analyze(ctx, _args)` block):

    (1) `def summarize_diff(ctx: Any, _args: list[str]) -> None:` →
    `from .skills.summarize_diff import run` then call `run(cwd=ctx.cwd,
    provider=ctx.provider, history=ctx.history, record=ctx.record,
    renderer=ctx.renderer, tools=ctx.tools, gate=ctx.gate)` (NO `args=` —
    agentic skill, signature has no `args` param). Register
    `SkillEntry(id="summarize-diff", description="Summarize the working-tree
    git diff as a structured PR description.", handler=summarize_diff,
    mutating=False)`.

    (2) `def audit_cognition(ctx: Any, _args: list[str]) -> None:` →
    `from .skills.audit_cognition import run` then call `run(...)` with the
    same seven kwargs (NO `args=`). Register
    `SkillEntry(id="audit-cognition", description="Audit project cognition
    for drift and propose an architecture update (never writes).",
    handler=audit_cognition, mutating=False)`.

    Note hyphenated `id` vs underscored module (RESEARCH Pitfall 1):
    `id="summarize-diff"` ↔ `from .skills.summarize_diff import run`;
    `id="audit-cognition"` ↔ `from .skills.audit_cognition import run`. After
    this edit there are exactly 5 `SkillEntry(` literals in the file.

    Edit `tests/skills/test_skills_smoke.py`: replace ONLY the bodies of
    `test_summarize_diff` and `test_audit_cognition` (currently
    `pytest.fail("not yet")` stubs). Do NOT modify `test_rename_symbol`,
    `test_voss_lint` (T7-02 green — leave green), `test_add_test`,
    `test_port_py_to_voss` (T7-04 stubs — leave as `pytest.fail`). CRITICAL:
    leave `test_registry_count` EXACTLY as is — it asserts the final count of
    7 and legitimately stays RED until T7-04 (T7-01-PLAN lines 138-143/
    233-234; T7-02-PLAN lines 167-179). Do NOT weaken it to `== 5`/`>= 5`.

    `test_summarize_diff` body: use the `git_repo` fixture (or
    `seed_git_repo`) to get a temp git tree; copy
    `tests/skills/fixtures/summarize-diff/README.md` into it and modify the
    working copy so `git diff` is non-empty (e.g. append a line, do NOT
    `git add`). Build a `Plan` whose `steps` include
    `ToolCall(name="git_diff", args={})` and whose
    `final_when_done="## Title\n...\n## Summary\n...\n## Changes\n..."`
    (RESEARCH lines 766-775). `provider = FakeProvider(plan)`. Import `run`
    from `voss.harness.skills.summarize_diff`; call it with
    `cwd=<git tree>`, `provider=provider`, `history=None`,
    `record=types.SimpleNamespace(model="fake", id="t")`,
    `renderer=PlainRenderer()`, `tools=make_toolset(<git tree>)`,
    `gate=PermissionGate(auto_yes=True)`. Assert: the run completes without
    raising; the agent issued the `git_diff` call (e.g. inspect
    `provider.calls` / the FakeProvider plan was consumed); the rendered
    final contains all three of `## Title`, `## Summary`, `## Changes`
    (capture renderer/stdout output, or assert against `plan.final_when_done`
    that the skill surfaced — choose the assertion the FakeProvider seam
    supports, mirroring the agentic-skill test pattern in T7-PATTERNS
    lines 613-639). Also assert NO mutation occurred: the git tree's tracked
    files are byte-identical before/after the run (read-only invariant) and
    `default_skill_registry().get("summarize-diff").mutating is False`.

    `test_audit_cognition` body: build a temp project dir; copy the T7-01
    fixture `tests/skills/fixtures/audit-cognition/.voss/architecture.md`
    into `<dir>/.voss/architecture.md` so `cognition.load(<dir>)` returns
    `initialized=True` with a non-None `architecture_frontmatter` (seed a
    git repo in `<dir>` if `drift_check` requires git metadata — use
    `seed_git_repo`). Snapshot the bytes of `<dir>/.voss/architecture.md`
    (and `<dir>/VOSS.md` if present) BEFORE the run. Build a `Plan` with
    `final_when_done="PROPOSAL: <one-paragraph proposal text>"`;
    `provider = FakeProvider(plan)`. Import `run` from
    `voss.harness.skills.audit_cognition`; call with `cwd=<dir>`,
    `provider=provider`, `history=None`,
    `record=types.SimpleNamespace(model="fake", id="t")`,
    `renderer=PlainRenderer()`, `tools=make_toolset(<dir>)`,
    `gate=PermissionGate(auto_yes=True)`. Assert: the run completes; the
    surfaced final contains `PROPOSAL:`; AND — the HARD invariant —
    `<dir>/.voss/architecture.md` is BYTE-IDENTICAL to the pre-run snapshot
    (and `VOSS.md` unchanged / still absent) — D-05/D-10/Pitfall 3, the
    block-on-high check for this plan. Also assert
    `default_skill_registry().get("audit-cognition").mutating is False`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "from voss.harness.skill_registry import default_skill_registry as d; r=d(); ids=set(r.ids()); assert {'analyze','rename-symbol','voss-lint-as-skill','summarize-diff','audit-cognition'} <= ids, ids; assert r.get('summarize-diff').mutating is False; assert r.get('audit-cognition').mutating is False; print('registry ok', sorted(ids))" && test "$(grep -c 'SkillEntry(' voss/harness/skill_registry.py)" -eq 5 && pytest tests/skills/test_skills_smoke.py::test_summarize_diff tests/skills/test_skills_smoke.py::test_audit_cognition tests/skills/test_skills_smoke.py::test_rename_symbol tests/skills/test_skills_smoke.py::test_voss_lint -q && python3 -c "import subprocess,sys; r=subprocess.run([sys.executable,'-m','pytest','tests/skills/test_skills_smoke.py::test_registry_count','-q'],capture_output=True); sys.exit(0 if r.returncode!=0 else 1)" && echo "EXPECTED: test_registry_count still RED until T7-04 (final-count guard NOT weakened)"</automated>
  </verify>
  <done>`default_skill_registry()` exposes `summarize-diff` (mutating=False) + `audit-cognition` (mutating=False) alongside T7-02's `analyze`/`rename-symbol`/`voss-lint-as-skill`; exactly 5 `SkillEntry(` literals (additive, T7-04 can append its final two). `test_summarize_diff` + `test_audit_cognition` pass green; `test_rename_symbol` + `test_voss_lint` remain green. `test_registry_count` still RED (final-7 guard, NOT weakened — T7-04 turns it green). `test_add_test`/`test_port_py_to_voss` remain untouched stubs.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| agentic skill (`audit-cognition`) → cognition/architecture files | The model is asked to propose an `architecture.md` update; the read-only contract (D-10) forbids the skill from applying it — the LLM may otherwise emit a write |
| agentic skill (`summarize-diff`) → working tree | A read-only skill that drives `run_turn` with the full toolset must not produce any file mutation |
| `.voss` companion source → `voss check` (CI gate) | The companion files are parsed by the already-wired CI `voss check voss/harness/skills/voss/` step; a syntactically invalid companion fails CI for the whole repo |
| FakeProvider plan → skill final output | The test stub controls `final_when_done`; the skill must surface it faithfully without side effects |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T7-03-01 | Tampering | `audit_cognition.run` no-write invariant | mitigate | THREE layers (RESEARCH Pitfall 3 two-layer + a structural code layer): (1) the prompt explicitly forbids writes and demands a `PROPOSAL:`-prefixed paragraph; (2) the module imports/uses NO write API (`fs_write`/`fs_edit`/`voss_md`/`Path.write_text`) — Task 2 verify greps that no write/`architecture.md`/`VOSS.md` reference exists in code; (3) Task 3's `test_audit_cognition` byte-compares `.voss/architecture.md` (and `VOSS.md`) before/after the run under FakeProvider. This is the block-on-high invariant for the plan. |
| T-T7-03-02 | Tampering | `summarize_diff.run` read-only invariant | mitigate | Skill code references no `fs_write`/`fs_edit`/`voss_md`/`.write_text` (Task 1 verify greps for their absence in code); `summarize-diff` registered `mutating=False`; Task 3's `test_summarize_diff` asserts the git tree's tracked files are byte-identical before/after the run. |
| T-T7-03-03 | Spoofing | `.voss` companion presented as exec path | accept | The companions are dogfood demonstrations only (D-05) — there is no `.voss`-skill loader (deferred, T7-CONTEXT). They are never executed as skills; only `voss check`-validated. No runtime trust is placed in them; module docstrings state "NOT the exec path". |
| T-T7-03-04 | Denial of Service | invalid `.voss` companion breaks CI | mitigate | Both companion shapes were probed against `python3 -m voss.cli check` during planning and exit 0; Task 1 & Task 2 each re-run `voss check` on their companion in `<verify>` before completion, so a non-passing file blocks the task rather than reaching CI. |
| T-T7-03-05 | Elevation of Privilege | agentic skill escalates via toolset | accept | Both skills pass the caller's `gate` straight through to `run_turn` (no toolset stripping, no permission bypass — D-11); the agent loop's existing gate enforcement applies to any tool the model calls. `summarize-diff`/`audit-cognition` are `mutating=False`; in `plan` mode the gate denies any mutating tool the model might attempt automatically. No skill-level permission code is added. |
| T-T7-03-SC | Tampering | npm/pip/cargo installs | mitigate | T7 introduces ZERO new packages (RESEARCH §"Package Legitimacy Audit": all deps existing — `voss.harness.agent`, `voss.harness.cognition`, `click`, stdlib `asyncio`/`pathlib`). No install task in this plan → no slopcheck / legitimacy checkpoint required. |

Block-on-high: T-T7-03-01 (`audit-cognition` writing `architecture.md`/
`VOSS.md` despite its read-only contract). Structurally prevented by the
three-layer defense and verified by Task 3's byte-identical assertion under
FakeProvider. No new dependencies, no network surface, no permission-gate code
modified.
</threat_model>

<verification>
Phase-level checks for this plan (run after all 3 tasks):

```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. Both handler modules parse and have the agentic run() signature (no args param)
python3 -c "import ast; [ast.parse(open(f).read()) for f in ('voss/harness/skills/summarize_diff.py','voss/harness/skills/audit_cognition.py')]"

# 2. summarize-diff: run_turn-driven, names the 3 stable headers, no write path in code
grep -q 'from ..agent import run_turn' voss/harness/skills/summarize_diff.py
python3 -c "s=open('voss/harness/skills/summarize_diff.py').read(); assert all(h in s for h in ('## Title','## Summary','## Changes'))"
python3 -c "import re;s=open('voss/harness/skills/summarize_diff.py').read();b=chr(10).join(l for l in s.splitlines() if not l.lstrip().startswith(chr(35)));assert not re.search(r'fs_write|fs_edit|\.write_text\(|voss_md',b)"

# 3. audit-cognition: cognition preamble, PROPOSAL marker, NO write/architecture path in code
grep -q 'from .. import cognition' voss/harness/skills/audit_cognition.py
python3 -c "import re;s=open('voss/harness/skills/audit_cognition.py').read();b=chr(10).join(l for l in s.splitlines() if not l.lstrip().startswith(chr(35)));assert 'cognition.load(' in b and 'cognition.drift_check(' in b;assert 'PROPOSAL:' in s;assert not re.search(r'fs_write|fs_edit|\.write_text\(|voss_md|architecture\.md|VOSS\.md',b)"

# 4. Both .voss companions voss check-pass
python3 -m voss.cli check voss/harness/skills/voss/summarize-diff.voss
python3 -m voss.cli check voss/harness/skills/voss/audit-cognition.voss
python3 -m voss.cli check voss/harness/skills/voss/   # whole companion dir (the CI gate)

# 5. Registry: 5 entries, correct mutating flags, additive (T7-04 can append)
python3 -c "from voss.harness.skill_registry import default_skill_registry as d;r=d();ids=set(r.ids());assert {'analyze','rename-symbol','voss-lint-as-skill','summarize-diff','audit-cognition'}<=ids;assert r.get('summarize-diff').mutating is False;assert r.get('audit-cognition').mutating is False"
test "$(grep -c 'SkillEntry(' voss/harness/skill_registry.py)" -eq 5

# 6. The two owned tests are green; T7-02's stay green; registry_count untouched/RED
pytest tests/skills/test_skills_smoke.py::test_summarize_diff tests/skills/test_skills_smoke.py::test_audit_cognition tests/skills/test_skills_smoke.py::test_rename_symbol tests/skills/test_skills_smoke.py::test_voss_lint -q
pytest tests/skills/test_skills_smoke.py::test_registry_count -q || echo "OK: registry_count still RED (final-7 guard, T7-04 turns it green)"

# 7. No whitespace damage
git diff --check
```
</verification>

<success_criteria>
- `voss/harness/skills/summarize_diff.py` and `voss/harness/skills/audit_cognition.py` exist, parse, and define `run(*, cwd, provider, history, record, renderer, tools, gate)` (agentic signature, no `args`).
- SKL-03 `summarize-diff`: drives `run_turn` via `asyncio.run`; prompt instructs the agent to call `git_diff` and emit ONLY markdown with the stable headers `## Title`, `## Summary`, `## Changes`; performs zero file mutations (no `fs_write`/`fs_edit`/`voss_md`/`.write_text` in code); `mutating=False`.
- SKL-05 `audit-cognition`: `cognition.load()` + `drift_check()` preamble (clean early-return when uninitialized / no frontmatter); prompt includes the drift status, forbids file writes, and contains the `PROPOSAL:` marker; NEVER writes `architecture.md`/`VOSS.md` (no write API referenced in code; test byte-compares the file before/after); `mutating=False`.
- Both `.voss` companions (`voss/harness/skills/voss/summarize-diff.voss`, `voss/harness/skills/voss/audit-cognition.voss`) exist and `python3 -m voss.cli check` exits 0 on each and on the whole `voss/harness/skills/voss/` dir.
- `default_skill_registry()` registers `summarize-diff` (mutating=False) and `audit-cognition` (mutating=False) appended after T7-02's three entries; exactly 5 `SkillEntry(` literals; edits additive so T7-04 appends its final two without conflict.
- `tests/skills/test_skills_smoke.py::test_summarize_diff` and `::test_audit_cognition` pass green; `test_rename_symbol` + `test_voss_lint` remain green.
- `test_registry_count` is NOT weakened — it still asserts the final 7 and stays RED until T7-04; `test_add_test`/`test_port_py_to_voss` remain untouched stubs.
- `git diff --check` is clean.
</success_criteria>

<output>
Create `.planning/phases/T7-skills-bootstrap/T7-03-SUMMARY.md` when done.
</output>
