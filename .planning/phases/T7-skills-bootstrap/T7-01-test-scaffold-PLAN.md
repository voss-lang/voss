---
phase: T7-skills-bootstrap
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/skills/__init__.py
  - tests/skills/conftest.py
  - tests/skills/test_skills_smoke.py
  - tests/skills/fixtures/rename-symbol/foo.py
  - tests/skills/fixtures/rename-symbol/caller.py
  - tests/skills/fixtures/add-test/target.py
  - tests/skills/fixtures/summarize-diff/README.md
  - tests/skills/fixtures/port-py-to-voss/classify_intent.py
  - tests/skills/fixtures/audit-cognition/.voss/architecture.md
  - tests/skills/fixtures/voss-lint/bad.voss
  - voss/harness/skills/voss/.gitkeep
  - .github/workflows/ci.yml
autonomous: true
requirements: [SKL-01, SKL-02, SKL-03, SKL-04, SKL-05, SKL-06]

must_haves:
  truths:
    - "Running `pytest tests/skills/test_skills_smoke.py --collect-only` discovers exactly 7 tests"
    - "All 7 smoke tests fail (red) with a 'not yet' message — none pass and none error on collection"
    - "`from tests.skills.conftest import FakeProvider` succeeds and the class implements both `complete()` and `stream()`"
    - "`tests/skills/conftest.py` exposes an autouse `isolated_state` fixture and a `seed_git_repo` helper that builds a temp git tree"
    - "All 6 `tests/skills/fixtures/<skill>/` seed directories exist with their seed files"
    - "`voss/harness/skills/voss/` directory exists and is tracked by git"
    - "`.github/workflows/ci.yml` runs `voss check voss/harness/skills/voss/` inside the `stub` job before the pytest step"
  artifacts:
    - path: "tests/skills/__init__.py"
      provides: "test package marker (matches tests/eval/__init__.py convention)"
    - path: "tests/skills/conftest.py"
      provides: "isolated_state autouse fixture, seed_git_repo helper, module-level FakeProvider"
      contains: "class FakeProvider"
      min_lines: 70
    - path: "tests/skills/test_skills_smoke.py"
      provides: "7 red stub tests, one per SKL-01..06 + test_registry_count"
      contains: "def test_registry_count"
    - path: "voss/harness/skills/voss/.gitkeep"
      provides: "directory placeholder so the .voss companion dir exists pre-T7-03/04"
    - path: ".github/workflows/ci.yml"
      provides: "CI gate that voss check-validates the .voss companion dir"
      contains: "voss check voss/harness/skills/voss"
  key_links:
    - from: "tests/skills/conftest.py"
      to: "tests/harness/test_agent_integration.py:30-102"
      via: "FakeProvider copied verbatim"
      pattern: "def stream\\(self, \\*\\*kwargs\\)"
    - from: "tests/skills/conftest.py"
      to: "tests/harness/conftest.py:28-42"
      via: "isolated_state autouse fixture ported"
      pattern: "XDG_STATE_HOME"
    - from: ".github/workflows/ci.yml"
      to: "voss/harness/skills/voss/"
      via: "voss check CI step in stub job"
      pattern: "voss\\.cli check voss/harness/skills/voss"
---

<objective>
Create the entire T7 test seam and shared scaffold so the four downstream
per-skill plans (T7-02, T7-03, T7-04) execute against a fixed, unambiguous
harness. This plan adds NO skill handlers, does NOT edit
`voss/harness/skill_registry.py`, and adds NO `SkillEntry` registrations — it
is a pure seam.

Purpose: Downstream plans turn the 7 stub tests green one cluster at a time.
The test names, fixture paths, `FakeProvider` location, and the
`voss/harness/skills/voss/` companion directory are contracts that T7-02/03/04
depend on verbatim — they must be final and correct here.

Output: `tests/skills/` package (`__init__.py`, `conftest.py`,
`test_skills_smoke.py` with 7 red stubs), 6 fixture seed-repo directories, the
`voss/harness/skills/voss/` directory, and a new `voss check` CI step in the
`stub` job of `.github/workflows/ci.yml`. Satisfies T7-VALIDATION Dimension 8
(every downstream per-skill task has an automated verify or a Wave 0
dependency landed here).
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
@.planning/phases/T7-skills-bootstrap/T7-PLAN-OUTLINE.md

<interfaces>
<!-- Contracts the executor needs. Extracted from live source — no codebase exploration required. -->

FakeProvider canonical source — tests/harness/test_agent_integration.py
  - Imports (lines 12-19): `from voss_runtime import EpisodicMemory`,
    `from voss_runtime.providers.base import ProviderResponse`,
    `from voss.harness.agent import Plan, ToolCall, run_turn`,
    `from voss.harness.permissions import PermissionGate`,
    `from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage`,
    `from voss.harness.render import PlainRenderer`,
    `from voss.harness.tools import make_toolset`
  - `class FakeProvider` spans lines 30-102 INCLUSIVE. It contains:
    `__init__(self, plan, cost=0.001)`, an `async def complete(...)`,
    `def stream(self, **kwargs)` returning an async generator that yields
    `TextDelta`, `ParsedPlan`, `Usage`, `Done`, and
    `def count_tokens(self, *, text, model)`.
  - The `_stream_index` guard makes call 0 emit the canned plan and call 1+
    emit a synthetic done `Plan`. This is the post-T1-05 contract (run_turn
    drives `provider.stream()`, not `complete()`). RESEARCH Pitfall 4.

isolated_state + git_repo analog — tests/harness/conftest.py
  - lines 28-31: `@pytest.fixture(autouse=True) def isolated_state(tmp_path, monkeypatch)`
    → `monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path)); return tmp_path`
  - lines 34-42: `@pytest.fixture def git_repo(tmp_path)` runs `git init`,
    `git config user.email t@t`, `git config user.name t`, writes
    `README.md` with `"# t\n"`, `git add .`, `git commit -m init`,
    returns `tmp_path` (all subprocess calls `cwd=tmp_path`,
    `check=True`, `capture_output=True`).

CI insertion point — .github/workflows/ci.yml (verified against live file)
  - `stub` job begins at line 32.
  - line 45: `- run: pip install -e ".[dev]"` (makes `voss check` available)
  - line 46: `- name: voss check harness sources (M4 DOG-06)`
  - line 47: `  run: python -m voss.cli check voss/harness/agent/`
  - line 48: `- run: python -m voss.cli check voss-demos/`
  - line 49: `- name: T1 grep gate — _substitute_placeholders is deleted (SPEC ITER-02)`
  - line 56: `- run: pytest -q -m "not live" --cov=voss_runtime --cov-report=term-missing`
  - The new T7 step inserts BETWEEN line 48 and line 49 (after the
    voss-demos check, before the T1 grep gate, well before the pytest run).
  - Other jobs in the file (`dep-audit`, `live`, `npm-version-sync`) must
    NOT be touched.

SkillRegistry shape (read-only context — DO NOT edit skill_registry.py here)
  - `voss/harness/skill_registry.py`: `default_skill_registry()` currently
    registers only `analyze`. `registry.ids()` returns a sorted list. After
    all of T7 it returns 7 ids. `test_registry_count` asserts this — it stays
    RED until T7-02/03/04 add registrations.

Test-package convention
  - Every `tests/<subdir>/` carries an `__init__.py` (tests/eval/__init__.py,
    tests/memory/__init__.py, tests/packaging/__init__.py, etc.).
    `tests/skills/__init__.py` MUST exist to match. (`tests/harness/` is the
    lone exception and is NOT the template to follow.)
  - `pyproject.toml [tool.pytest.ini_options]`: `testpaths = ["tests"]`,
    `asyncio_mode = "auto"`. No new markers needed — skill tests are
    deterministic (no `@pytest.mark.live`/`slow`).
  - `voss/harness/skills/` already exists with `__init__.py` + `analyze.py`.
    T7-01 only ADDS the `voss/` subdir under it; it does not modify the
    package or `analyze.py`.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create tests/skills package — __init__, conftest (isolated_state + seed_git_repo + FakeProvider)</name>
  <read_first>
    tests/harness/test_agent_integration.py (lines 1-110 — FakeProvider class 30-102 + its imports 12-19, copy verbatim)
    tests/harness/conftest.py (lines 28-42 — isolated_state + git_repo fixtures)
    tests/eval/__init__.py (the empty-package-marker convention)
  </read_first>
  <action>
    Create `tests/skills/__init__.py` as an empty file (package marker —
    matches the `tests/eval/__init__.py` / `tests/memory/__init__.py`
    convention; required because `testpaths = ["tests"]` and every sibling
    test dir has one).

    Create `tests/skills/conftest.py` with three things:

    (1) An autouse `isolated_state` fixture ported verbatim from
    `tests/harness/conftest.py:28-31`: takes `tmp_path` and `monkeypatch`,
    calls `monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))`, returns
    `tmp_path`. This is the test-isolation security control — it prevents any
    skill test from writing session JSON / permission state into the real
    `~/.local/state` or the real working tree.

    (2) A `seed_git_repo` helper. Provide it BOTH as a pytest fixture named
    `git_repo` (so downstream plans can request `git_repo: Path` exactly like
    `tests/harness/conftest.py:34-42` does) AND as a plain module-level
    function `seed_git_repo(root: Path) -> Path` that the fixture delegates to
    (so a downstream test can seed a git tree at an arbitrary fixture-copy
    path, not only `tmp_path`). `seed_git_repo` must: `subprocess.run`
    `git init`, `git config user.email t@t`, `git config user.name t` (all
    `cwd=root`, `check=True`, `capture_output=True`); if no `README.md`
    exists in `root`, write `README.md` with `"# t\n"`; then `git add .`,
    `git commit -m init`. It must NOT clobber pre-seeded fixture files — only
    add a README when one is absent — and it must operate strictly inside the
    passed `root` (no path traversal, never the real project repo). Return
    `root`. The `git_repo` fixture body is just `return seed_git_repo(tmp_path)`.

    (3) The `FakeProvider` class copied VERBATIM from
    `tests/harness/test_agent_integration.py:30-102` (the full class body:
    `__init__`, `async def complete`, `def stream`, `def count_tokens`),
    together with the imports it needs at module top:
    `from voss.harness.agent import Plan, ToolCall, run_turn`,
    `from voss.harness.permissions import PermissionGate`,
    `from voss.harness.providers import Done, ParsedPlan, TextDelta, Usage`,
    `from voss.harness.render import PlainRenderer`,
    `from voss.harness.tools import make_toolset`,
    `from voss_runtime.providers.base import ProviderResponse`. FakeProvider
    is a module-level class, NOT a fixture, so downstream tests construct it
    inline with different `Plan` objects. Do not rename it, do not strip
    `complete()`, do not strip `count_tokens()` — RESEARCH Pitfall 4
    (post-T1-05 `run_turn` calls `provider.stream()`; a FakeProvider missing
    `stream()` raises AttributeError). Re-exporting the supporting imports
    (`Plan`, `ToolCall`, `PermissionGate`, `PlainRenderer`, `make_toolset`)
    from conftest is acceptable — downstream test files import them anyway.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && python -c "from tests.skills.conftest import FakeProvider, seed_git_repo; assert all(hasattr(FakeProvider,m) for m in ('complete','stream','count_tokens')); print('ok')"</automated>
  </verify>
  <done>`tests/skills/__init__.py` exists (empty). `tests/skills/conftest.py` imports cleanly; `FakeProvider` has `complete`, `stream`, `count_tokens`; `seed_git_repo` is importable and the `git_repo` fixture delegates to it. The autouse `isolated_state` fixture sets `XDG_STATE_HOME`.</done>
</task>

<task type="auto">
  <name>Task 2: Create 7 red stub tests + all 6 fixture seed-repo directories</name>
  <read_first>
    tests/skills/conftest.py (created in Task 1 — the seam this consumes)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (§"Wave 0 Gaps" lines 884-897; §"Skill-by-Skill Implementation Notes" lines 599-674 — exact fixture file shapes)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (§"Phase Requirements → Test Map" lines 866-877 — exact test names + per-req commands)
  </read_first>
  <action>
    Create `tests/skills/test_skills_smoke.py` with EXACTLY these 7 test
    functions, each a stub whose body is a single `pytest.fail("not yet")`:
    `test_rename_symbol` (SKL-01), `test_add_test` (SKL-02),
    `test_summarize_diff` (SKL-03), `test_port_py_to_voss` (SKL-04),
    `test_audit_cognition` (SKL-05), `test_voss_lint` (SKL-06),
    `test_registry_count`. These names are FINAL contracts — T7-02 turns
    `test_rename_symbol`/`test_voss_lint`/`test_registry_count` green, T7-03
    turns `test_summarize_diff`/`test_audit_cognition` green, T7-04 turns
    `test_add_test`/`test_port_py_to_voss` green. Add a module docstring
    noting each test's owning downstream plan. `import pytest` only — do NOT
    import skill handlers (they do not exist yet; importing them would make
    collection error instead of cleanly fail). Functions take no fixture
    params at this stage (downstream plans add `git_repo`/`tmp_path` params
    when they implement the body).

    Create the 6 fixture seed directories with the exact shapes from
    T7-RESEARCH §"Skill-by-Skill Implementation Notes":

    - `tests/skills/fixtures/rename-symbol/foo.py` → contains `def foo():`
      returning a constant; `tests/skills/fixtures/rename-symbol/caller.py` →
      `from foo import foo` then a call to `foo()`. (SKL-01 renames
      `foo`→`bar` across both; T7-02 asserts the resulting `git diff`.)
    - `tests/skills/fixtures/add-test/target.py` → a public function
      `def add(a, b): return a + b`, no test file present. (SKL-02 generates
      `tests/test_target.py`; T7-04 asserts `pytest --collect-only` finds
      `test_add`.)
    - `tests/skills/fixtures/summarize-diff/README.md` → a short README whose
      presence lets a downstream test introduce an unstaged modification
      before invoking the skill. (SKL-03 summarizes the diff.)
    - `tests/skills/fixtures/port-py-to-voss/classify_intent.py` → a simple
      function returning a string based on its input (maps to the
      `samples/classify.voss` shape). (SKL-04 translates it to `.voss`;
      T7-04 asserts `voss check` exits 0 on the generated file.)
    - `tests/skills/fixtures/audit-cognition/.voss/architecture.md` → a
      pre-initialized cognition file with realistic frontmatter (`git_head`,
      `analyzed_at`, `file_count`, `analyzer_version`) plus a short
      `# Architecture` body — model it on the `pre_m8_architecture_md`
      fixture in `tests/harness/conftest.py:108-125` so a downstream test can
      trigger drift. (SKL-05 emits a proposal and must NOT write this file.)
    - `tests/skills/fixtures/voss-lint/bad.voss` → a `.voss` source with a
      known, deterministic analyzer violation (e.g. a reference to an
      undefined variable inside an `fn`). The seeded finding must be stable
      so T7-02 can assert the emitted JSON contains it. Do not over-engineer
      — one clear violation is enough.

    Borrow the M5 `task.toml`+`fixture/` directory SHAPE conceptually only
    (T7-CONTEXT D-01): these are plain seed dirs with static files — NO
    `task.toml`, NO dependency on `tests/eval/golden/`, NO M5 import. Per
    T7-PATTERNS §"No Analog Found", there is no prior skill-fixture analog;
    create them as plain directories with static seed files. Every fixture
    dir has at least one tracked seed file, so no `.gitkeep` is needed inside
    fixtures.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/skills/test_skills_smoke.py --collect-only -q 2>&1 | grep -E "7 (tests collected|selected)" && python -c "import pathlib; b=pathlib.Path('tests/skills/fixtures'); req=['rename-symbol/foo.py','rename-symbol/caller.py','add-test/target.py','summarize-diff/README.md','port-py-to-voss/classify_intent.py','audit-cognition/.voss/architecture.md','voss-lint/bad.voss']; missing=[p for p in req if not (b/p).exists()]; assert not missing, missing; print('fixtures ok')"</automated>
  </verify>
  <done>`pytest tests/skills/test_skills_smoke.py --collect-only` reports exactly 7 tests; running them yields 7 failed (each `pytest.fail("not yet")`), zero collection errors. All 7 fixture seed files listed above exist with the specified content.</done>
</task>

<task type="auto">
  <name>Task 3: Create voss/harness/skills/voss/ dir + add T7 voss check step to ci.yml stub job</name>
  <read_first>
    .github/workflows/ci.yml (lines 32-56 — the live `stub` job; voss check steps at 46-48 and the T1 grep gate at 49 are the exact anchors)
    voss/harness/skills/ (live dir — already has __init__.py + analyze.py; T7-01 only adds the voss/ subdir)
    .planning/phases/T7-skills-bootstrap/T7-RESEARCH.md (§"CI Configuration Requirements" lines 779-798)
  </read_first>
  <action>
    Create the directory `voss/harness/skills/voss/` and add a tracked
    placeholder `voss/harness/skills/voss/.gitkeep` (empty) so the directory
    exists in git before T7-03/T7-04 add the `.voss` companion files. Do NOT
    add an `__init__.py` here — this dir holds `.voss` source files, not a
    Python package (RESEARCH §"Recommended Project Structure" notes the
    `__init__.py` may be omitted; `voss check` walks `.voss` files
    regardless). Do NOT create any handler modules and do NOT touch
    `voss/harness/skill_registry.py` — this plan is a pure seam.

    Edit `.github/workflows/ci.yml`: in the `stub` job (starts line 32),
    insert a new step immediately AFTER the existing
    `- run: python -m voss.cli check voss-demos/` line (line 48) and BEFORE
    the `- name: T1 grep gate ...` step (line 49). The new step:
    `- name: voss check skills voss companions (T7)` with
    `run: python -m voss.cli check voss/harness/skills/voss/`. Match the
    exact 6-space step indentation and the `- name:` / `run:` two-line shape
    of the adjacent M4 DOG-06 step (lines 46-47). Touch only the `stub` job;
    do NOT modify the `dep-audit`, `live`, or `npm-version-sync` jobs.
    `voss check` over an empty / `.gitkeep`-only dir must exit 0 (it walks
    `*.voss` and finds none) so the CI job is not failed pre-T7-03. The
    `pip install -e ".[dev]"` step (line 45) already makes `voss check`
    available; no extra install step needed.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && test -d voss/harness/skills/voss && git ls-files --error-unmatch voss/harness/skills/voss/.gitkeep && grep -q "voss check voss/harness/skills/voss" .github/workflows/ci.yml && python -c "import yaml; d=yaml.safe_load(open('.github/workflows/ci.yml')); runs=[s.get('run','') for s in d['jobs']['stub']['steps']]; assert any('voss/harness/skills/voss' in r for r in runs), 'step missing from stub job'; print('ci step ok')" && python -m voss.cli check voss/harness/skills/voss/ && echo "voss check exit 0 on empty dir"</automated>
  </verify>
  <done>`voss/harness/skills/voss/` exists and `.gitkeep` is git-tracked. `.github/workflows/ci.yml` parses as valid YAML; the `stub` job contains a step running `python -m voss.cli check voss/harness/skills/voss/`; no other job modified. `voss check` on the empty dir exits 0.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test process → real filesystem / `~/.local/state` | Skill tests must not write session JSON, permission state, or any artifact into the real user state dir or the real working tree |
| test fixture seed dirs → real git repo | `seed_git_repo` runs `git init`/`commit`; must operate only inside the passed temp/fixture `root`, never the project repo |
| CI step → repo path argument | The new `voss check` CI step takes a fixed literal path, not user/PR-controlled input |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T7-01 | Tampering | test isolation | mitigate | `isolated_state` autouse fixture (ported verbatim from `tests/harness/conftest.py:28-31`) repoints `XDG_STATE_HOME` to `tmp_path` for every test — no test can write to the real state dir. Verified by Task 1 (`isolated_state` present + autouse). |
| T-T7-02 | Tampering | `seed_git_repo` helper | mitigate | `seed_git_repo(root)` runs every `git`/`subprocess` call with `cwd=root` (a `tmp_path` or fixture-copy dir under pytest's tmp), `check=True`, `capture_output=True`; never accepts an absolute outside path, never touches the project repo. The `git_repo` fixture only passes `tmp_path`. |
| T-T7-03 | Tampering | CI `voss check` step | accept | The new step's path argument is a hardcoded literal `voss/harness/skills/voss/` in the workflow file — not derived from PR title, branch, or any attacker-controlled input. No injection surface. Empty-dir run exits 0 (no side effects). |
| T-T7-04 | Information Disclosure | fixture seed files | accept | Seed files (`foo.py`, `target.py`, `bad.voss`, fixture `architecture.md`) contain only synthetic, non-sensitive content authored in this plan — no secrets, no real project data, no exfiltration path. |
| T-T7-SC | Tampering | npm/pip/cargo installs | mitigate | T7 introduces ZERO new packages (RESEARCH §"Package Legitimacy Audit": all deps are existing stdlib/project modules). No install task in this plan → no slopcheck / legitimacy checkpoint required. |

Block-on-high: none. No mutating skill handlers, no new dependencies, no
network surface, no permission-gate code touched in this plan (pure test
seam). The two `mitigate` items are satisfied by copying the already-audited
harness isolation pattern verbatim.
</threat_model>

<verification>
Phase-level checks for this plan (run after all 3 tasks):

```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. Exactly 7 stub tests collected, all RED, zero collection errors
pytest tests/skills/test_skills_smoke.py --collect-only -q 2>&1 | grep -E "7 (tests collected|selected)"
pytest tests/skills/test_skills_smoke.py -q 2>&1 | grep -E "7 failed"

# 2. Seam importable
python -c "from tests.skills.conftest import FakeProvider, seed_git_repo; assert all(hasattr(FakeProvider,m) for m in ('complete','stream','count_tokens'))"

# 3. All 6 fixture dirs + seed files present
python -c "import pathlib;b=pathlib.Path('tests/skills/fixtures');assert all((b/p).exists() for p in ['rename-symbol/foo.py','rename-symbol/caller.py','add-test/target.py','summarize-diff/README.md','port-py-to-voss/classify_intent.py','audit-cognition/.voss/architecture.md','voss-lint/bad.voss'])"

# 4. .voss companion dir tracked + CI gate wired + valid YAML
test -d voss/harness/skills/voss && git ls-files --error-unmatch voss/harness/skills/voss/.gitkeep
grep -q "voss check voss/harness/skills/voss" .github/workflows/ci.yml
python -c "import yaml;yaml.safe_load(open('.github/workflows/ci.yml'))"

# 5. Seam does NOT leak into the skill registry (pure seam invariant)
git diff --stat -- voss/harness/skill_registry.py | grep -q . && echo "FAIL: registry edited (forbidden in T7-01)" || echo "OK: skill_registry.py untouched"
ls voss/harness/skills/*.py | grep -vq "analyze.py" && echo "FAIL: handler module added (forbidden in T7-01)" || echo "OK: only analyze.py present"

# 6. No whitespace damage
git diff --check
```
</verification>

<success_criteria>
- `pytest tests/skills/test_skills_smoke.py --collect-only` discovers exactly 7 tests, named `test_rename_symbol`, `test_add_test`, `test_summarize_diff`, `test_port_py_to_voss`, `test_audit_cognition`, `test_voss_lint`, `test_registry_count`.
- Running the 7 stubs yields 7 failed (`pytest.fail("not yet")`), zero collection errors, zero passes.
- `tests/skills/conftest.py` provides an autouse `isolated_state` fixture, a `seed_git_repo` helper + `git_repo` fixture, and a module-level `FakeProvider` with `complete()`, `stream()`, and `count_tokens()` (copied verbatim from `tests/harness/test_agent_integration.py:30-102`).
- All 6 `tests/skills/fixtures/<skill>/` seed-repo directories exist with the seed files specified in T7-RESEARCH §"Skill-by-Skill Implementation Notes".
- `voss/harness/skills/voss/` exists, git-tracked via `.gitkeep`; `voss check` on it exits 0.
- `.github/workflows/ci.yml` is valid YAML; the `stub` job runs `python -m voss.cli check voss/harness/skills/voss/` after the `voss-demos` check and before the T1 grep gate; no other job modified.
- Pure-seam invariant holds: `voss/harness/skill_registry.py` is unmodified and no new handler module exists under `voss/harness/skills/`.
- `git diff --check` is clean.
</success_criteria>

<output>
Create `.planning/phases/T7-skills-bootstrap/T7-01-SUMMARY.md` when done.
</output>
