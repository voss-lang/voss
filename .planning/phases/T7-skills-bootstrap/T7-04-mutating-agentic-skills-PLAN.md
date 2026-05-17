---
phase: T7-skills-bootstrap
plan: 04
type: execute
wave: 4
depends_on: [T7-01, T7-02, T7-03]
files_modified:
  - voss/harness/skills/add_test.py
  - voss/harness/skills/port_py_to_voss.py
  - voss/harness/skills/voss/add-test.voss
  - voss/harness/skills/voss/port-py-to-voss.voss
  - voss/harness/skill_registry.py
  - tests/skills/test_skills_smoke.py
autonomous: true
requirements: [SKL-02, SKL-04]

must_haves:
  truths:
    - "Running `add-test` drives an agent turn via run_turn that locates a public function in the target repo and writes `tests/test_<module>.py` containing a deliberately failing assertion THROUGH the gated `fs_write` tool"
    - "`pytest --collect-only` on the fixture repo discovers the test `add-test` generated (proves SKL-02 D-02 post-condition)"
    - "Running `port-py-to-voss <source.py>` drives a run_turn that translates the source Python to `.voss` (classify/support/research sample shapes) and writes it THROUGH gated `fs_write`"
    - "`voss check` exits 0 on the `.voss` file `port-py-to-voss` generated (proves SKL-04 D-02 post-condition)"
    - "Both skills run in `plan` mode WITHOUT mutating any file and without escalation/bypass — the gated write path refuses cleanly (D-09/D-11)"
    - "`port-py-to-voss` never writes outside the fixture repo cwd — a test asserts no file is created or modified outside the temp project root (path-traversal mitigated by fs_write's jail_path)"
    - "`voss check voss/harness/skills/voss/add-test.voss` exits 0 and `voss check voss/harness/skills/voss/port-py-to-voss.voss` exits 0"
    - "`default_skill_registry()` registers `add-test` (mutating=True) and `port-py-to-voss` (mutating=True) appended after T7-03's five entries — exactly 7 SkillEntry literals total"
    - "`tests/skills/test_skills_smoke.py::test_add_test`, `::test_port_py_to_voss`, AND `::test_registry_count` all pass green — test_registry_count asserts exactly 7 entries and this is the plan that finally satisfies it"
  artifacts:
    - path: "voss/harness/skills/add_test.py"
      provides: "SKL-02 agentic mutating handler — run_turn via asyncio.run; agent locates a public fn and writes a failing pytest test via gated fs_write"
      contains: "def run"
      min_lines: 25
    - path: "voss/harness/skills/port_py_to_voss.py"
      provides: "SKL-04 agentic mutating handler — run_turn via asyncio.run; args[0]=source path; agent translates Python to .voss via gated fs_write"
      contains: "def run"
      min_lines: 25
    - path: "voss/harness/skills/voss/add-test.voss"
      provides: "SKL-02 .voss companion (dogfood demo, voss-check-pass, NOT exec path)"
      contains: "fn findPublicFn"
    - path: "voss/harness/skills/voss/port-py-to-voss.voss"
      provides: "SKL-04 .voss companion modeling research.voss shape (dogfood demo, voss-check-pass, NOT exec path)"
      contains: "fn translatePython"
    - path: "voss/harness/skill_registry.py"
      provides: "two final SkillEntry registrations (add-test, port-py-to-voss) appended after T7-03's — registry now totals 7"
      contains: "add-test"
    - path: "tests/skills/test_skills_smoke.py"
      provides: "test_add_test + test_port_py_to_voss bodies turned green AND test_registry_count finally green (asserts 7)"
      contains: "def test_add_test"
  key_links:
    - from: "voss/harness/skill_registry.py"
      to: "voss.harness.skills.add_test.run"
      via: "default_skill_registry() inner handler imports + calls run(...)"
      pattern: "from .skills.add_test import run"
    - from: "voss/harness/skill_registry.py"
      to: "voss.harness.skills.port_py_to_voss.run"
      via: "default_skill_registry() inner handler imports + calls run(...)"
      pattern: "from .skills.port_py_to_voss import run"
    - from: "voss/harness/skills/add_test.py"
      to: "voss.harness.agent.run_turn"
      via: "asyncio.run(run_turn(prompt, ...)) — agent writes via gated fs_write"
      pattern: "from ..agent import run_turn"
    - from: "voss/harness/skills/port_py_to_voss.py"
      to: "voss.harness.agent.run_turn"
      via: "asyncio.run(run_turn(prompt, ...)) — args[0] source path, gated fs_write output"
      pattern: "from ..agent import run_turn"
    - from: "tests/skills/test_skills_smoke.py"
      to: "voss.harness.skill_registry.default_skill_registry"
      via: "test_registry_count asserts len(registry.ids()) == 7"
      pattern: "== 7"
---

<objective>
Implement the two mutating agentic skills (D-07 agentic, D-09
`mutating=True`): SKL-02 `add-test` (agent locates a public function and
writes a pytest test containing a deliberately failing assertion to
`tests/test_<module>.py`) and SKL-04 `port-py-to-voss` (agent translates an
input Python file — `args[0]` — to `.voss` using the classify/support/research
sample shapes). Both write ONLY through the existing gated `fs_write`/`fs_edit`
tools so the standard permission gate + mode rules apply — no skill-level
escalation or bypass (D-09/D-11). Ship a `voss check`-passing `.voss` companion
for each (D-05 dogfood demonstration, NOT the runtime exec path; the
`port-py-to-voss` companion models the `samples/research.voss` shape per
T7-PATTERNS). Register both in `default_skill_registry()` and turn the final
three smoke tests green — including `test_registry_count`, which asserts the
final 7-entry count and is satisfied for the first time by THIS plan.

Purpose: This is the FINAL plan of phase T7. After it the whole phase
verifies: 7 registry entries, all 7 smoke tests green, 4 `.voss` companions
`voss check`-clean, CI gate active. The block-on-high security invariant for
this plan is that both mutating skills route every write through the gated
tools (so `plan` mode refuses cleanly) and that `port-py-to-voss` cannot write
outside the cwd (path-traversal — mitigated by `fs_write`'s `jail_path` and
asserted by a test).

Output: `voss/harness/skills/add_test.py`,
`voss/harness/skills/port_py_to_voss.py`, two `.voss` companions under
`voss/harness/skills/voss/`, two `SkillEntry` registrations appended in
`voss/harness/skill_registry.py` (registry total → 7), and green bodies for
`test_add_test`, `test_port_py_to_voss`, and `test_registry_count` in
`tests/skills/test_skills_smoke.py`.
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
@.planning/phases/T7-skills-bootstrap/T7-03-readonly-agentic-skills-PLAN.md

<interfaces>
<!-- Contracts the executor needs. Extracted from live source — no codebase exploration required. -->

Agentic handler template — voss/harness/skills/analyze.py (live, full file, read this run)
  - Imports: `from __future__ import annotations`, `import asyncio`,
    `import click`, `from pathlib import Path`, `from ..agent import
    run_turn`. (`analyze.py` also imports `cognition, voss_md`; the two
    T7-04 skills need NEITHER — no cognition preamble, no staging fold.)
  - `def run(*, cwd: Path, provider, history, record, renderer, tools, gate)
    -> None:` — EXACT keyword-only signature (analyze.py:25-34). Agentic
    skills do NOT add an `args` param. SKL-04 needs the source path; obtain it
    from the registry handler via the SECOND positional handler arg (see
    registration interface) — pass it INTO `run` as an extra keyword-only
    param `source: str | None = None` (this is acceptable: only deterministic
    T7-02 skills used the generic `args` list; SKL-04 takes a single named
    `source`). SKL-02 takes no positional args.
  - Agentic call shape (analyze.py:55-68), copy verbatim, swap only the
    prompt: `asyncio.run(run_turn(prompt, tools=tools, cwd=cwd,
    renderer=renderer, model=record.model, provider=provider,
    history=history, permissions=gate, cognition=None,
    session_id=record.id))`. `run()` stays a SYNC function — never add
    `async`; `asyncio.run` is the bridge (RESEARCH A3: slash/CLI call sites
    have no running loop).

run_turn signature — voss/harness/agent.py:412 (live)
  - `async def run_turn(task: str, *, tools, cwd, renderer,
    confidence_threshold=0.60, token_budget=60_000, model=None, provider=None,
    history=None, permissions=None, session_id=None, cognition=None,
    prior_context=None, voss_md_text=None) -> TurnResult`.

Gated write tools — voss/harness/tools.py (live)
  - `fs_write` (is_mutating=True, `invoke(path: str, content: str)`),
    `fs_edit` (is_mutating=True, `invoke(path: str, old: str, new: str)`).
  - The agent loop INSIDE `run_turn` calls `gate.check(...)` automatically
    before every mutating tool dispatch — agentic skills do NOT self-enforce
    the gate (that landmine is only for the deterministic T7-02 skills which
    run OUTSIDE `run_turn`). T7-04 skills pass the caller's `gate` straight
    through `permissions=gate`; in `plan` mode the gate denies `fs_write`
    automatically (`mode_allows` returns `(False, "denied by mode plan")`),
    so the agent's write is refused and nothing is mutated — clean refusal,
    no escalation (D-09/D-11, RESEARCH Security Domain).
  - `fs_write`/`fs_edit` confine writes to `cwd` via `jail_path` (RESEARCH
    Security Domain — SKL-04 path-traversal mitigation). Skills must NOT call
    `Path.write_text`/`open(...,'w')`/`shell_run` directly — all mutation
    flows through these tools.

SkillEntry / default_skill_registry — voss/harness/skill_registry.py (live, full file)
  - `@dataclass(frozen=True) class SkillEntry: id: str; description: str;
    handler: SkillHandler; mutating: bool = False`.
  - `SkillHandler = Callable[[Any, list[str]], None]` — handler is
    `(ctx: Any, args: list[str]) -> None`. `SkillRegistry.register/get/ids
    (sorted)/entries`.
  - The existing `analyze` inner handler is
    `def analyze(ctx: Any, _args: list[str]) -> None:` → `from .cli import
    _handle_analyze` → call with `cwd/provider/history/record/renderer/tools/
    gate` unpacked from `ctx`; then ONE
    `registry.register(SkillEntry(id="analyze", ..., mutating=True))`;
    `return registry`.
  - AFTER T7-02 + T7-03 the body of `default_skill_registry()` contains, in
    order: `analyze`, `rename_symbol`, `voss_lint_as_skill` (T7-02),
    `summarize_diff`, `audit_cognition` (T7-03), then `return registry` —
    exactly 5 `SkillEntry(` literals. T7-04 inserts the FINAL TWO
    inner+`register` blocks BETWEEN the `audit_cognition` registration and
    `return registry` (strictly additive, preserving prior block order). After
    T7-04 there are exactly 7 `SkillEntry(` literals.
  - SKL-02 `add-test` is agentic with no positional args → inner handler
    `def add_test(ctx: Any, _args: list[str]) -> None:` (mirror the `analyze`
    `_args` shape, do NOT forward it). SKL-04 `port-py-to-voss` needs the
    source path → inner handler `def port_py_to_voss(ctx: Any, args:
    list[str]) -> None:` and pass `source=args[0] if args else None` into
    `run`.
  - Hyphenated `id` vs underscored module (RESEARCH Pitfall 1):
    `id="add-test"` ↔ `from .skills.add_test import run`;
    `id="port-py-to-voss"` ↔ `from .skills.port_py_to_voss import run`.

Test seam — tests/skills/conftest.py (created by T7-01, DO NOT modify)
  - Autouse `isolated_state` (XDG sandbox per test). Module-level
    `FakeProvider` (verbatim from `tests/harness/test_agent_integration.py:
    30-102`): `FakeProvider(plan)`; `stream()` emits the canned `plan` on
    call 0 and a synthetic done plan after — `run_turn` drives
    `provider.stream()` (Pitfall 4). `Plan`, `ToolCall`, `PermissionGate`,
    `PlainRenderer`, `make_toolset` are re-exported from conftest — import
    them from `tests.skills.conftest`.
  - `git_repo` fixture + `seed_git_repo(root) -> Path` helper (git
    init+config+README+commit, returns root). `seed_git_repo` only seeds the
    passed root.
  - Fixtures landed by T7-01:
    `tests/skills/fixtures/add-test/target.py` (a public function
    `def add(a, b): return a + b`, NO test file present — SKL-02 generates
    `tests/test_target.py`, `pytest --collect-only` must then find `test_add`);
    `tests/skills/fixtures/port-py-to-voss/classify_intent.py` (a simple
    function returning a string based on input — maps to the
    `samples/classify.voss` shape; SKL-04 translates it to `.voss`).

Smoke-test contract — tests/skills/test_skills_smoke.py (T7-01 created; T7-02/03 edited)
  - Holds 7 functions. T7-01 stubbed all as `pytest.fail("not yet")` EXCEPT
    `test_registry_count`, whose REAL body asserts the FINAL count of 7
    (`len(default_skill_registry().ids()) == 7`, i.e. `analyze` + 6). T7-02
    turned `test_rename_symbol`/`test_voss_lint` green; T7-03 turned
    `test_summarize_diff`/`test_audit_cognition` green. Both T7-02 and T7-03
    explicitly LEFT `test_registry_count` RED and FORBADE weakening it
    (T7-01-PLAN lines 138-143/233-234; T7-02-PLAN lines 167-179; T7-03-PLAN
    lines 194-202).
  - T7-04 replaces ONLY the bodies of `test_add_test` and
    `test_port_py_to_voss` (the last two `pytest.fail("not yet")` stubs).
    It MUST NOT touch `test_rename_symbol`/`test_voss_lint`/
    `test_summarize_diff`/`test_audit_cognition` (already green — leave green).
  - `test_registry_count` GOES GREEN AUTOMATICALLY once T7-04 registers the
    final two skills — its body is already the correct `== 7` assertion. T7-04
    does NOT rewrite it; it MUST NOT change the assertion to a different
    number. Confirm its current form by reading the file (it should be a
    single `assert len(default_skill_registry().ids()) == 7` against the
    7-entry final count). If — and only if — T7-01 left it as a
    `pytest.fail("not yet")` stub instead of the real assertion (contrary to
    the T7-01 contract), replace its body with exactly
    `from voss.harness.skill_registry import default_skill_registry;
    assert len(default_skill_registry().ids()) == 7`. Never assert any value
    other than 7.

.voss companion constructs — PROBED against `python3 -m voss.cli check` THIS planning run, both exit 0
  - `add-test.voss` shape (exit 0 verified): a `# add-test.voss` comment
    header, then `fn findPublicFn(path: string) -> string {` with body
    `ctx(budget: 3000 tokens) { yield ask("... " + path) }`. Mirrors
    `samples/classify.voss` string-param + `+` concat and the
    `samples/research.voss:10` / `voss/harness/agent/loop.voss:14`
    `ctx(budget: N tokens)` precedent.
  - `port-py-to-voss.voss` shape (exit 0 verified) — models
    `samples/research.voss` (T7-PATTERNS lines 457-489): a
    `# port-py-to-voss.voss` comment header, then
    `fn translatePython(pySource: string) -> string {` with body
    `ctx(budget: 6000 tokens) { try { include pySource; yield ask("Translate
    this Python source to .voss using the classify/support/research sample
    shapes as guides.") } catch e { return "translation failed: " + e } }`.
    `include <expr>`, `try { } catch e { }`, and `return "..." + e` inside a
    `ctx` body are all valid (`samples/research.voss:11-18`).
  - The `voss/harness/skills/voss/` directory exists (T7-01 `.gitkeep`); the
    CI `voss check voss/harness/skills/voss/` step is already wired (T7-01
    Task 3). Adding `.voss` files there is sufficient — no CI edit in this
    plan.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Implement SKL-02 add-test handler + companion .voss</name>
  <read_first>
    voss/harness/skills/add_test.py (file being created — confirm it does not exist)
    voss/harness/skills/analyze.py (lines 10-19 imports; lines 25-68 — exact run() signature + asyncio.run(run_turn(...)) call shape to copy, swapping only the prompt)
    voss/harness/skills/summarize_diff.py (T7-03 output — the closest agentic-skill module shape to mirror; confirm its run() signature has no args param)
    voss/harness/skills/voss/add-test.voss (file being created — confirm it does not exist; dir + .gitkeep exist from T7-01)
    samples/classify.voss (string param + `+` concat reference) and samples/research.voss (lines 10-18 — ctx(budget: N tokens) { yield ask(...) } reference)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 118-194 — agentic skill module shape + per-skill prompt notes; lines 412-443 — add-test.voss target shape)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (lines 621-630 — SKL-02 notes incl. pytest framework confirmation; lines 754-775 — FakeProvider/Plan steps with ToolCall)
    tests/skills/fixtures/add-test/target.py (T7-01 fixture — confirm the public fn it seeds)
  </read_first>
  <action>
    Create `voss/harness/skills/add_test.py`. Module header docstring states:
    SKL-02, agentic (D-07 — invokes a model turn via `run_turn`), mutating
    (D-09 — `mutating=True`); the agent locates a public function and writes a
    pytest test through the gated `fs_write` tool, so the standard permission
    gate + mode rules apply with NO skill-level escalation or bypass
    (D-09/D-11). pytest is the confirmed project test framework (RESEARCH
    discretion call, line 623 — `pyproject.toml [tool.pytest.ini_options]`).

    Imports: `from __future__ import annotations`, `import asyncio`,
    `from pathlib import Path`, `from ..agent import run_turn`. Do NOT import
    `cognition`/`voss_md`; do NOT import any `fs_write`/`fs_edit` helper
    directly (the agent calls the tool through `run_turn`, the skill does
    not).

    Define `def run(*, cwd: Path, provider, history, record, renderer, tools,
    gate) -> None:` — the EXACT keyword-only signature from
    `analyze.py:25-34` (no `args` param: SKL-02 takes no positional CLI args).
    Keep `run` SYNC.

    Build a single `prompt` string instructing the agent to: (a) locate a
    public function in the project (under `cwd`); (b) write a pytest test
    module at `tests/test_<module>.py` (where `<module>` is the source
    module's name) that imports the function and asserts on it; (c) the test
    MUST contain a deliberately failing assertion (e.g. an assertion that the
    function returns a value it does not) so the planted test is RED by
    design — name this requirement explicitly in the prompt; (d) write the
    file using the `fs_write` tool (name the tool in the prompt so the model
    routes the write through it — this keeps the gate in the loop). Instruct
    the agent NOT to use any shell command and NOT to write anywhere except
    the `tests/` directory under the project root.

    Drive the agent with the `analyze.py:55-68` call shape verbatim, swapping
    only the prompt: `asyncio.run(run_turn(prompt, tools=tools, cwd=cwd,
    renderer=renderer, model=record.model, provider=provider,
    history=history, permissions=gate, cognition=None,
    session_id=record.id))`. Do NOT post-process, do NOT call `fs_write`/
    `fs_edit` from the skill itself, do NOT pass a stripped toolset — the
    gate enforcement and the cwd jail are provided by `run_turn`'s tool
    dispatch + `fs_write`'s `jail_path`. The skill returns `None`
    (SkillHandler contract).

    Create the companion `voss/harness/skills/voss/add-test.voss` (dogfood
    demonstration of composability, D-05, NOT the runtime exec path; state
    that in a comment header). Use the PROBED-passing shape (exit 0 this
    planning run): a `# add-test.voss` comment header, then
    `fn findPublicFn(path: string) -> string {` with body
    `ctx(budget: 3000 tokens) { yield ask("...<instruction to find a public
    function and write a failing pytest test for it>... " + path) }` (use
    `+ path` string concatenation to reference the param, mirroring
    `samples/classify.voss:4`). It must `voss check`-pass (Task 1 verify runs
    it). Do NOT register the skill here (Task 3 owns the registry edit).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "import ast; ast.parse(open('voss/harness/skills/add_test.py').read()); print('ast ok')" && grep -q "from ..agent import run_turn" voss/harness/skills/add_test.py && python3 -c "import re; s=open('voss/harness/skills/add_test.py').read(); b=chr(10).join(l for l in s.splitlines() if not l.lstrip().startswith('#')); assert 'fs_write' in s, 'prompt should name the gated fs_write tool'; assert not re.search(r'\.write_text\(|open\([^)]*[\x27\x22]w|shell_run|run_turn.*tools=\[\]', b), 'no direct write / shell / stripped toolset in code'; print('add_test ok')" && python3 -m voss.cli check voss/harness/skills/voss/add-test.voss && echo "voss check add-test.voss exit 0"</automated>
  </verify>
  <done>`voss/harness/skills/add_test.py` parses, imports `run_turn`, names the gated `fs_write` tool in its prompt, performs no direct write/shell in code and passes the full toolset to `run_turn`. `voss/harness/skills/voss/add-test.voss` exists and `python3 -m voss.cli check` on it exits 0. Not yet registered (Task 3).</done>
</task>

<task type="auto">
  <name>Task 2: Implement SKL-04 port-py-to-voss handler (source arg, cwd-confined) + companion .voss</name>
  <read_first>
    voss/harness/skills/port_py_to_voss.py (file being created — confirm it does not exist)
    voss/harness/skills/add_test.py (Task 1 output — mirror its agentic module shape + run() signature; this one ADDS a source kw param)
    voss/harness/skills/analyze.py (lines 10-19 imports; lines 25-68 run()/run_turn call shape)
    voss/harness/skills/voss/port-py-to-voss.voss (file being created — confirm it does not exist)
    samples/research.voss (lines 6-19 + 30-47 — the agent/ctx/try-catch/include shape the companion models, per T7-PATTERNS)
    samples/classify.voss and samples/support.voss (the sample shapes the SKL-04 prompt instructs the agent to translate toward)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 118-195 — agentic skill shape + SKL-04 prompt note; lines 457-489 — port-py-to-voss.voss target shape modeling research.voss)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (lines 642-652 — SKL-04 notes + target shapes; lines 918-922 — Security Domain path-traversal mitigation via fs_write jail_path)
    tests/skills/fixtures/port-py-to-voss/classify_intent.py (T7-01 fixture — the source the test feeds to the skill)
  </read_first>
  <action>
    Create `voss/harness/skills/port_py_to_voss.py`. Module header docstring
    states: SKL-04, agentic (D-07), mutating (D-09 — `mutating=True`); the
    agent translates an input Python file (`args[0]`, passed in as the
    `source` kw param) to `.voss` and writes it through the gated `fs_write`
    tool — standard gate + mode rules apply, no escalation/bypass
    (D-09/D-11). Path-traversal is mitigated by `fs_write`'s `jail_path`
    confining the write to `cwd` (RESEARCH Security Domain lines 918-922); the
    skill MUST NOT construct or write raw filesystem paths itself.

    Imports: `from __future__ import annotations`, `import asyncio`,
    `import click`, `from pathlib import Path`, `from ..agent import
    run_turn`. No `cognition`/`voss_md`; no direct `fs_write`/`fs_edit`
    helper import.

    Define `def run(*, cwd: Path, provider, history, record, renderer, tools,
    gate, source: str | None = None) -> None:` — the `analyze.py:25-34`
    keyword-only signature PLUS one extra keyword-only param `source` (the
    registry handler passes `source=args[0] if args else None`; this is the
    single named source path — NOT the generic `args` list the T7-02
    deterministic skills used). Keep `run` SYNC.

    Argument validation: if `source is None`, emit
    `click.echo("usage: port-py-to-voss <source.py>", err=True)` and `return`
    (no turn). Do NOT resolve `source` to an absolute filesystem path in the
    skill and do NOT read/stat it via the OS — pass it to the agent in the
    prompt as a project-relative path; the agent reads it through the gated
    read tool and writes the result through the gated `fs_write` tool, all
    confined to `cwd` by `jail_path`.

    Build a single `prompt` string instructing the agent to: (a) read the
    Python source at the given relative path (state the path in the prompt
    via the `source` value); (b) translate it to `.voss` choosing the closest
    of the `samples/classify.voss` (simple fn + `probable<T>` + confidence
    gate), `samples/support.voss` (`prompt`/`memory.episodic`/`match
    similar`), or `samples/research.voss` (`agent`/`spawn`/`gather`/
    `within/fallback`/`try/catch`) shapes as a guide; (c) write the
    translated `.voss` to a sibling path (same stem, `.voss` extension)
    INSIDE the project root using the `fs_write` tool (name the tool in the
    prompt); (d) explicitly: do NOT write anywhere outside the project
    directory, do NOT use shell. The translated file must be valid enough
    that `voss check` exits 0 (the post-condition D-02 / SKL-04).

    Drive with the `analyze.py:55-68` call shape verbatim, swapping only the
    prompt: `asyncio.run(run_turn(prompt, tools=tools, cwd=cwd,
    renderer=renderer, model=record.model, provider=provider,
    history=history, permissions=gate, cognition=None,
    session_id=record.id))`. Do NOT post-process or write from the skill, do
    NOT pass a stripped toolset. Return `None`.

    Create the companion `voss/harness/skills/voss/port-py-to-voss.voss`
    (dogfood demo, D-05, NOT exec path; comment header says so). Use the
    PROBED-passing shape (exit 0 this planning run) that MODELS
    `samples/research.voss` per T7-PATTERNS: a `# port-py-to-voss.voss`
    comment header, then `fn translatePython(pySource: string) -> string {`
    with body `ctx(budget: 6000 tokens) { try { include pySource; yield
    ask("Translate this Python source to .voss using the classify/support/
    research sample shapes as guides.") } catch e { return "translation
    failed: " + e } }`. Must `voss check`-pass (Task 2 verify runs it). Do
    NOT register here (Task 3).
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "import ast; ast.parse(open('voss/harness/skills/port_py_to_voss.py').read()); print('ast ok')" && grep -q "from ..agent import run_turn" voss/harness/skills/port_py_to_voss.py && grep -q "source" voss/harness/skills/port_py_to_voss.py && python3 -c "import re; s=open('voss/harness/skills/port_py_to_voss.py').read(); b=chr(10).join(l for l in s.splitlines() if not l.lstrip().startswith('#')); assert 'fs_write' in s, 'prompt should name the gated fs_write tool'; assert 'def run(' in b and 'source' in b, 'run() must accept source kw'; assert not re.search(r'\.write_text\(|open\([^)]*[\x27\x22]w|shell_run', b), 'no direct write / shell in code'; print('port_py_to_voss ok')" && grep -q "fn translatePython" voss/harness/skills/voss/port-py-to-voss.voss && python3 -m voss.cli check voss/harness/skills/voss/port-py-to-voss.voss && echo "voss check port-py-to-voss.voss exit 0"</automated>
  </verify>
  <done>`voss/harness/skills/port_py_to_voss.py` parses, imports `run_turn`, defines `run(..., source=None)`, names the gated `fs_write` tool in its prompt, performs no direct write/shell in code. `voss/harness/skills/voss/port-py-to-voss.voss` exists, contains `fn translatePython`, and `python3 -m voss.cli check` on it exits 0. Not yet registered (Task 3).</done>
</task>

<task type="auto">
  <name>Task 3: Register both skills (registry → 7) + turn test_add_test, test_port_py_to_voss & test_registry_count green</name>
  <read_first>
    voss/harness/skill_registry.py (the full live file post-T7-03 — 5 SkillEntry blocks: analyze, rename_symbol, voss_lint_as_skill, summarize_diff, audit_cognition; the analyze block is the registration template)
    voss/harness/skills/add_test.py (Task 1 output — confirm run() kwargs, no args param)
    voss/harness/skills/port_py_to_voss.py (Task 2 output — confirm run() takes source kw)
    .planning/phases/T7-skills-bootstrap/T7-PATTERNS.md (lines 34-114 — registration pattern + the id/module/mutating table rows for add-test & port-py-to-voss)
    tests/skills/test_skills_smoke.py (post-T7-03 — replace ONLY test_add_test + test_port_py_to_voss bodies; CONFIRM the current test_registry_count body asserts == 7)
    tests/skills/conftest.py (T7-01 — FakeProvider + re-exported Plan/ToolCall/PermissionGate/PlainRenderer/make_toolset)
    tests/skills/fixtures/add-test/target.py and tests/skills/fixtures/port-py-to-voss/classify_intent.py (T7-01 fixtures)
    .planning/phases/T7-skills-bootstrap/T7-01-test-scaffold-PLAN.md (lines 138-143, 233-234 — the registry-count contract: it asserts the FINAL 7 and T7-04 is the plan that satisfies it)
    .planning/phases/T7-skills-bootstrap/T7-02-deterministic-skills-PLAN.md (lines 167-179 — reaffirms registry-count contract / additive ordering)
    .planning/phases/T7-skills-bootstrap/T7-03-readonly-agentic-skills-PLAN.md (lines 194-202 — reaffirms registry-count contract; lines 380-409 — additive registration ordering)
  </read_first>
  <action>
    Edit `voss/harness/skill_registry.py`. Inside `default_skill_registry()`,
    AFTER the existing `audit_cognition` `registry.register(...)` block
    (T7-03's last registration) and BEFORE `return registry`, append the
    FINAL TWO registrations mirroring the `analyze` template exactly (inner
    function unpacking `ctx`, then `registry.register(...)`). Keep T7-02's and
    T7-03's five blocks untouched and in order; append strictly so the file
    ends with exactly 7 `SkillEntry(` literals:

    (1) `def add_test(ctx: Any, _args: list[str]) -> None:` →
    `from .skills.add_test import run` then call `run(cwd=ctx.cwd,
    provider=ctx.provider, history=ctx.history, record=ctx.record,
    renderer=ctx.renderer, tools=ctx.tools, gate=ctx.gate)` (NO `args=` /
    `source=` — SKL-02 takes no positional args; mirror the `analyze`
    `_args`-ignored shape). Register `SkillEntry(id="add-test",
    description="Locate a public function and generate a failing pytest
    test.", handler=add_test, mutating=True)`.

    (2) `def port_py_to_voss(ctx: Any, args: list[str]) -> None:` →
    `from .skills.port_py_to_voss import run` then call `run(cwd=ctx.cwd,
    provider=ctx.provider, history=ctx.history, record=ctx.record,
    renderer=ctx.renderer, tools=ctx.tools, gate=ctx.gate, source=args[0] if
    args else None)`. Register `SkillEntry(id="port-py-to-voss",
    description="Translate a Python source file to .voss.",
    handler=port_py_to_voss, mutating=True)`.

    Note hyphenated `id` vs underscored module (RESEARCH Pitfall 1):
    `id="add-test"` ↔ `from .skills.add_test import run`;
    `id="port-py-to-voss"` ↔ `from .skills.port_py_to_voss import run`. After
    this edit there are EXACTLY 7 `SkillEntry(` literals in the file.

    Edit `tests/skills/test_skills_smoke.py`: replace ONLY the bodies of
    `test_add_test` and `test_port_py_to_voss` (currently `pytest.fail("not
    yet")` stubs). Do NOT modify `test_rename_symbol`, `test_voss_lint`
    (T7-02 green — leave green), `test_summarize_diff`, `test_audit_cognition`
    (T7-03 green — leave green). For `test_registry_count`: READ its current
    body. Per the T7-01 contract it is already the real assertion
    `len(default_skill_registry().ids()) == 7` (T7-01-PLAN lines 138-143/
    233-234) and goes green automatically now that the registry has 7 entries
    — do NOT rewrite or change the number. ONLY if T7-01 left it as a
    `pytest.fail("not yet")` stub (contrary to its contract), replace its body
    with exactly: import `default_skill_registry` from
    `voss.harness.skill_registry` and `assert
    len(default_skill_registry().ids()) == 7`. Never assert any number other
    than 7.

    `test_add_test` body: copy `tests/skills/fixtures/add-test/target.py`
    into a fresh temp project dir (`tmp_path`) — seed a git repo with
    `seed_git_repo` if helpful. Build a `Plan` whose `final_when_done`
    instructs completion and whose `steps` include a
    `ToolCall(name="fs_write", args={"path": "tests/test_target.py",
    "content": <a pytest test source string that imports `add` from
    `target` and contains a deliberately failing assertion, e.g. `def
    test_add():\n    assert add(1, 2) == 99`>})` (FakeProvider replays this
    plan; the harness will dispatch the `fs_write` tool through the gate —
    RESEARCH lines 766-775). `provider = FakeProvider(plan)`. Import `run`
    from `voss.harness.skills.add_test`; call it with `cwd=<temp dir>`,
    `provider=provider`, `history=None`, `record=types.SimpleNamespace(
    model="fake", id="t")`, `renderer=PlainRenderer()`,
    `tools=make_toolset(<temp dir>)`, `gate=PermissionGate(auto_yes=True)`.
    Assert: `<temp dir>/tests/test_target.py` now exists; `pytest
    --collect-only` run against `<temp dir>` (via `subprocess.run([sys
    .executable, "-m", "pytest", "--collect-only", "-q",
    "tests/test_target.py"], cwd=<temp dir>, capture_output=True)`) exits 0
    and its stdout names `test_add` (the SKL-02 D-02 post-condition). Then a
    SECOND invocation with `gate=PermissionGate(mode="plan")` on a clean copy
    of the fixture (no `tests/` dir) MUST leave the project free of any
    `tests/test_target.py` — the gated write refuses cleanly in `plan` mode,
    no escalation (D-09/D-11). Also assert
    `default_skill_registry().get("add-test").mutating is True`.

    `test_port_py_to_voss` body: copy
    `tests/skills/fixtures/port-py-to-voss/classify_intent.py` into a fresh
    temp project dir. Build a `Plan` whose `steps` include a
    `ToolCall(name="fs_write", args={"path": "classify_intent.voss",
    "content": <a minimal valid .voss source string that `voss check`
    accepts — e.g. a `fn` with a `return`; reuse the classify shape>})`.
    `provider = FakeProvider(plan)`. Import `run` from
    `voss.harness.skills.port_py_to_voss`; call with `cwd=<temp dir>`,
    `provider=provider`, `history=None`, `record=types.SimpleNamespace(
    model="fake", id="t")`, `renderer=PlainRenderer()`,
    `tools=make_toolset(<temp dir>)`, `gate=PermissionGate(auto_yes=True)`,
    `source="classify_intent.py"`. Assert: `<temp dir>/classify_intent.voss`
    exists and `subprocess.run([sys.executable, "-m", "voss.cli", "check",
    "classify_intent.voss"], cwd=<temp dir>, capture_output=True).returncode
    == 0` (the SKL-04 D-02 post-condition). PATH-TRAVERSAL ASSERTION
    (block-on-high): snapshot the set of files OUTSIDE `<temp dir>` is not
    relied upon — instead assert the only new file is inside `<temp dir>`
    (e.g. every path the FakeProvider plan wrote resolves under `<temp
    dir>`; and a control test where the plan's `fs_write` `path` is
    `"../escape.voss"` results in NO file created at `<temp dir>.parent /
    "escape.voss"` because `fs_write`'s `jail_path` confines it). Also run a
    `gate=PermissionGate(mode="plan")` invocation and assert NO `.voss` file
    was written (clean refusal). Assert
    `default_skill_registry().get("port-py-to-voss").mutating is True`.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python3 -c "from voss.harness.skill_registry import default_skill_registry as d; r=d(); ids=set(r.ids()); assert {'analyze','rename-symbol','voss-lint-as-skill','summarize-diff','audit-cognition','add-test','port-py-to-voss'} == ids, sorted(ids); assert len(r.ids())==7, len(r.ids()); assert r.get('add-test').mutating is True; assert r.get('port-py-to-voss').mutating is True; print('registry ok 7', sorted(ids))" && test "$(grep -c 'SkillEntry(' voss/harness/skill_registry.py)" -eq 7 && pytest tests/skills/test_skills_smoke.py::test_add_test tests/skills/test_skills_smoke.py::test_port_py_to_voss tests/skills/test_skills_smoke.py::test_registry_count -q && grep -q "== 7" tests/skills/test_skills_smoke.py && pytest tests/skills/test_skills_smoke.py -q && echo "ALL 7 SMOKE TESTS GREEN"</automated>
  </verify>
  <done>`default_skill_registry()` exposes exactly 7 entries (`analyze` + 6) with `add-test` (mutating=True) + `port-py-to-voss` (mutating=True) appended last; exactly 7 `SkillEntry(` literals. `test_add_test`, `test_port_py_to_voss`, AND `test_registry_count` (asserts `== 7`) all pass green; the four T7-02/T7-03 tests remain green; the full `tests/skills/test_skills_smoke.py` suite is 7/7 green. `plan`-mode invocations of both skills mutate nothing (clean refusal, no escalation); `port-py-to-voss` writes confined to cwd (jail_path).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| agentic mutating skill (`add-test`, `port-py-to-voss`) → working tree | Both skills drive `run_turn` and the model issues `fs_write` calls; the write MUST flow through the gated tool so the permission gate + mode rules apply — no skill-level escalation or bypass (D-09/D-11) |
| permission mode (`plan`) → mutating agentic skill | In `plan` mode the gated `fs_write`/`fs_edit` path must refuse cleanly (`"denied by mode plan"`) and the skill must mutate nothing — no escalation, no direct-write fallback |
| `port-py-to-voss` source arg + agent-chosen output path → filesystem | The source path is caller-supplied (`args[0]`); the agent picks the `.voss` output path. A write must NOT escape the project `cwd` (path traversal) |
| `.voss` companion source → `voss check` (CI gate) | The companions are parsed by the already-wired CI `voss check voss/harness/skills/voss/` step; a syntactically invalid companion fails CI for the whole repo |
| FakeProvider plan → skill write/output | The test stub controls the plan's `fs_write` steps; the skill must surface them through the gated tool dispatch without side effects beyond the gate's allowance |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T7-04-01 | Elevation of Privilege | `add_test`/`port_py_to_voss` mutation path | mitigate | Both skills drive `run_turn` and pass the caller's `gate` straight through `permissions=gate` (no toolset stripping, no skill-level permission code). The agent loop's automatic `gate.check(...)` fires before every `fs_write` dispatch. Task 1 & 2 verify greps that no `Path.write_text`/`open(...,'w')`/`shell_run` exists in skill code and no stripped toolset is passed. Task 3's `plan`-mode invocations assert ZERO mutation. Block-on-high invariant for this plan. |
| T-T7-04-02 | Tampering | `plan`-mode gated write path | mitigate | In `plan` mode `mode_allows` returns `(False, "denied by mode plan")` for `fs_write` automatically inside `run_turn`; the agent's write is refused and nothing is mutated. Task 3's `test_add_test` and `test_port_py_to_voss` each include a `PermissionGate(mode="plan")` invocation that asserts no `tests/test_target.py` / no `.voss` file was created — a structural test the bypass cannot pass silently (T5 D-12 / analyze.py precedent). |
| T-T7-04-03 | Tampering | `port-py-to-voss` path traversal (write outside cwd) | mitigate | The skill never constructs raw filesystem paths or calls `Path.write_text` — all writes flow through the gated `fs_write` tool whose `jail_path` confines writes to `cwd` (RESEARCH Security Domain lines 918-922). Task 2 verify forbids direct writes in code; Task 3's `test_port_py_to_voss` includes a control where the plan's `fs_write` path is `"../escape.voss"` and asserts NO file is created at `<tmp>.parent / "escape.voss"` (jail_path enforced). |
| T-T7-04-04 | Tampering | `add-test` writing outside the `tests/` dir / arbitrary file | accept | The prompt instructs the agent to write only under `tests/`; even if the model deviates, `fs_write`'s `jail_path` still confines the write to `cwd`, and the only security-relevant boundary (escape from the project root) is already covered by T-T7-04-03's jail_path control. A wrong-but-in-tree path is a correctness issue caught by `test_add_test`'s `pytest --collect-only` post-condition, not a security breach. No additional control. |
| T-T7-04-05 | Denial of Service | invalid `.voss` companion breaks CI | mitigate | Both companion shapes were PROBED against `python3 -m voss.cli check` during planning and exit 0; Task 1 & Task 2 each re-run `voss check` on their companion in `<verify>` before completion, so a non-passing file blocks the task rather than reaching the repo-wide CI gate. |
| T-T7-04-06 | Spoofing | `.voss` companion presented as exec path | accept | The companions are dogfood demonstrations only (D-05) — there is no `.voss`-skill loader (deferred, T7-CONTEXT). They are never executed as skills; only `voss check`-validated. Module/companion headers state "NOT the exec path". No runtime trust placed in them. |
| T-T7-04-SC | Tampering | npm/pip/cargo installs | mitigate | T7 introduces ZERO new packages (RESEARCH §"Package Legitimacy Audit": all deps existing — `voss.harness.agent`, `click`, stdlib `asyncio`/`pathlib`; tests use stdlib `subprocess`/`sys`). No install task in this plan → no slopcheck / legitimacy checkpoint required. |

Block-on-high: T-T7-04-01 / T-T7-04-02 / T-T7-04-03 (mutating agentic skills
must route every write through the gated tools so `plan` mode refuses cleanly,
and `port-py-to-voss` must not write outside `cwd`). Structurally prevented by
passing the caller's `gate` straight through `run_turn` (no skill-level
permission code, no toolset stripping, no direct writes — Task 1/2 verify) and
verified by Task 3's `plan`-mode no-mutation assertions plus the path-traversal
control. No new dependencies, no network surface, no permission-gate code
modified.
</threat_model>

<verification>
Phase-level checks for this plan (run after all 3 tasks):

```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. Both handler modules parse; add_test has agentic sig (no args), port_py_to_voss adds source kw
python3 -c "import ast; [ast.parse(open(f).read()) for f in ('voss/harness/skills/add_test.py','voss/harness/skills/port_py_to_voss.py')]"
grep -q 'from ..agent import run_turn' voss/harness/skills/add_test.py
grep -q 'from ..agent import run_turn' voss/harness/skills/port_py_to_voss.py
grep -q 'source' voss/harness/skills/port_py_to_voss.py

# 2. Both name the gated fs_write tool in the prompt; no direct write / shell / stripped toolset in code
python3 -c "import re; [exec('s=open(f).read(); b=chr(10).join(l for l in s.splitlines() if not l.lstrip().startswith(chr(35))); assert \"fs_write\" in s; assert not re.search(r\"\\.write_text\\(|shell_run\", b)') for f in ('voss/harness/skills/add_test.py','voss/harness/skills/port_py_to_voss.py')]"

# 3. Both .voss companions voss check-pass + the whole companion dir (4 files now)
python3 -m voss.cli check voss/harness/skills/voss/add-test.voss
python3 -m voss.cli check voss/harness/skills/voss/port-py-to-voss.voss
python3 -m voss.cli check voss/harness/skills/voss/

# 4. Registry: exactly 7 entries, correct mutating flags, full expected id set
python3 -c "from voss.harness.skill_registry import default_skill_registry as d;r=d();ids=set(r.ids());assert ids=={'analyze','rename-symbol','voss-lint-as-skill','summarize-diff','audit-cognition','add-test','port-py-to-voss'},sorted(ids);assert len(r.ids())==7;assert r.get('add-test').mutating is True;assert r.get('port-py-to-voss').mutating is True"
test "$(grep -c 'SkillEntry(' voss/harness/skill_registry.py)" -eq 7

# 5. test_registry_count asserts == 7 (not weakened to any other number) and is GREEN
grep -q "== 7" tests/skills/test_skills_smoke.py
pytest tests/skills/test_skills_smoke.py::test_registry_count -q

# 6. The two owned tests green; ALL 7 smoke tests green (phase-complete signal)
pytest tests/skills/test_skills_smoke.py::test_add_test tests/skills/test_skills_smoke.py::test_port_py_to_voss -q
pytest tests/skills/test_skills_smoke.py -q

# 7. No whitespace damage
git diff --check
```
</verification>

<success_criteria>
- `voss/harness/skills/add_test.py` and `voss/harness/skills/port_py_to_voss.py` exist, parse, and define `run(*, cwd, provider, history, record, renderer, tools, gate[, source=None])` (agentic signature; `port_py_to_voss` adds the `source` kw).
- SKL-02 `add-test`: drives `run_turn` via `asyncio.run`; prompt instructs the agent to locate a public function and write a pytest test with a deliberately failing assertion via the gated `fs_write` tool; no direct write/shell in code; `mutating=True`. `pytest --collect-only` on the fixture finds the generated `test_add` (D-02 post-condition).
- SKL-04 `port-py-to-voss`: drives `run_turn`; `source` = `args[0]`; prompt instructs translation to `.voss` (classify/support/research shapes) and a gated `fs_write`; no direct write/shell in code; `mutating=True`. `voss check` exits 0 on the generated `.voss` (D-02 post-condition); writes confined to `cwd` (`fs_write` `jail_path`), asserted by a path-traversal control test.
- Both skills in `plan` mode mutate nothing and refuse cleanly — no escalation/bypass (D-09/D-11), asserted by `plan`-mode test invocations.
- Both `.voss` companions (`voss/harness/skills/voss/add-test.voss`, `voss/harness/skills/voss/port-py-to-voss.voss`) exist and `python3 -m voss.cli check` exits 0 on each and on the whole `voss/harness/skills/voss/` dir; `port-py-to-voss.voss` models the `samples/research.voss` shape (T7-PATTERNS).
- `default_skill_registry()` registers `add-test` (mutating=True) and `port-py-to-voss` (mutating=True) appended after T7-03's five entries; exactly 7 `SkillEntry(` literals; the id set is exactly the 7 expected ids.
- `tests/skills/test_skills_smoke.py::test_add_test`, `::test_port_py_to_voss`, AND `::test_registry_count` (asserts exactly `== 7`, not weakened) all pass green; the four T7-02/T7-03 tests remain green; the full smoke suite is 7/7 green.
- `git diff --check` is clean.
</success_criteria>

<output>
Create `.planning/phases/T7-skills-bootstrap/T7-04-SUMMARY.md` when done.
</output>
