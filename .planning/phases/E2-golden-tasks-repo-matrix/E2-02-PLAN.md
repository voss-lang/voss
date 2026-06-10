---
phase: E2-golden-tasks-repo-matrix
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/eval/matrix/py-01-analyze/fixture/pyproject.toml
  - tests/eval/matrix/py-01-analyze/fixture/calc.py
  - tests/eval/matrix/py-01-analyze/fixture/test_calc.py
  - tests/eval/matrix/py-03-approved-edit/fixture/pyproject.toml
  - tests/eval/matrix/py-03-approved-edit/fixture/calc.py
  - tests/eval/matrix/py-03-approved-edit/fixture/test_calc.py
  - tests/eval/matrix/py-04-validation/fixture/pyproject.toml
  - tests/eval/matrix/py-04-validation/fixture/calc.py
  - tests/eval/matrix/py-04-validation/fixture/test_calc.py
  - tests/eval/matrix/py-02-plan-only/fixture/calc.py
  - tests/eval/matrix/py-05-resume/fixture/notes.txt
  - tests/eval/matrix/py-06-fetch-summarize/fixture/README.md
autonomous: true
requirements: [EVGLD-01]
must_haves:
  truths:
    - "Each Python shape fixture (py-01/03/04) is a flat 3-file repo (pyproject.toml + calc.py + test_calc.py) with an editable add() function"
    - "python3 -m pytest test_calc.py -q exits 0 inside any of the three shape fixtures"
    - "The three Python-only-task fixtures (py-02/05/06) are byte-copies of their golden analogs"
  artifacts:
    - path: "tests/eval/matrix/py-01-analyze/fixture/calc.py"
      provides: "Editable add(a,b) source for analyze cognition"
      contains: "def add"
    - path: "tests/eval/matrix/py-03-approved-edit/fixture/test_calc.py"
      provides: "pytest target that imports calc.add"
      contains: "from calc import add"
    - path: "tests/eval/matrix/py-04-validation/fixture/pyproject.toml"
      provides: "Manifest so analyze can name pyproject tooling"
      contains: "name = \"calc\""
  key_links:
    - from: "tests/eval/matrix/py-*/fixture/test_calc.py"
      to: "tests/eval/matrix/py-*/fixture/calc.py"
      via: "from calc import add (flat layout, no pip install)"
      pattern: "from calc import"
---

<objective>
Build the six Python matrix fixture directories under `tests/eval/matrix/py-*/fixture/`. Three shape-sensitive cells (py-01-analyze, py-03-approved-edit, py-04-validation) each get an identical flat 3-file calc repo with an editable `add()` function. Three language-agnostic cells (py-02-plan-only, py-05-resume, py-06-fetch-summarize) reuse the existing golden fixtures verbatim (RESEARCH Open Q3: duplicate, do not symlink — fixture isolation copies per task dir).

Purpose: Provides the Python project shape the runner copies + checks in an isolated temp dir (EVGLD-01, D-01).
Output: Six `py-*/fixture/` directories, each self-contained and ≤ 5 files (D-01 limit).
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/E2-golden-tasks-repo-matrix/E2-RESEARCH.md
@.planning/phases/E2-golden-tasks-repo-matrix/E2-PATTERNS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Build the three Python shape fixtures (py-01, py-03, py-04)</name>
  <files>tests/eval/matrix/py-01-analyze/fixture/{pyproject.toml,calc.py,test_calc.py}, tests/eval/matrix/py-03-approved-edit/fixture/{pyproject.toml,calc.py,test_calc.py}, tests/eval/matrix/py-04-validation/fixture/{pyproject.toml,calc.py,test_calc.py}</files>
  <read_first>
    - E2-RESEARCH.md §Python Fixture lines 357-385 (VERIFIED locally: flat layout, `python3 -m pytest test_calc.py -q` passes; src/ layout breaks imports per Pitfall 3 lines 618-621)
    - E2-PATTERNS.md §`tests/eval/matrix/py-*/fixture/` lines 252-283 (exact file bodies; analog `tests/eval/golden/02-plan-only/fixture/calc.py`)
    - tests/eval/golden/02-plan-only/fixture/calc.py (existing Python fixture shape — confirms a bare add() module is the established analog)
  </read_first>
  <action>
    Create three IDENTICAL flat fixture trees (one per shape cell). For each of py-01-analyze, py-03-approved-edit, py-04-validation, write `fixture/pyproject.toml` containing a `[project]` table with `name = "calc"` and `version = "0.1.0"` (no other keys — keeps it minimal and gives analyze a `pyproject` token to name). Write `fixture/calc.py` defining `def add(a: int, b: int) -> int:` returning `a + b` (typed signature; this is the approved-edit rename target → `sum_two`). Write `fixture/test_calc.py` that does `from calc import add` and defines `def test_add() -> None:` asserting `add(1, 2) == 3`. Use FLAT layout only (calc.py + test_calc.py at fixture root, NOT src/) — `python3 -m pytest test_calc.py` resolves the import at cwd without `pip install -e .` (Pitfall 3). Do NOT add a `[tool.pytest]` section or any pytest config — the bare `pytest test_calc.py` invocation is sufficient. The three trees are byte-identical; the difference between cells lives in their task.toml (plan 05), not the fixture.
  </action>
  <acceptance_criteria>
    - For each of the three dirs: `cd <fixture> && python3 -m pytest test_calc.py -q` exits 0 (run via: `.venv/bin/python -c "import subprocess,sys; [sys.exit(r.returncode) for d in ['py-01-analyze','py-03-approved-edit','py-04-validation'] for r in [subprocess.run(['python3','-m','pytest','test_calc.py','-q'], cwd='tests/eval/matrix/'+d+'/fixture')] if r.returncode]"` exits 0)
    - `grep -l "def add" tests/eval/matrix/py-0{1,3,4}-*/fixture/calc.py` lists all three
    - Each fixture dir contains exactly 3 files: `find tests/eval/matrix/py-01-analyze/fixture -type f | wc -l` equals 3
    - `grep -c "src/" tests/eval/matrix/py-01-analyze/fixture/test_calc.py` equals 0 (flat layout, no src import)
  </acceptance_criteria>
  <verify>
    <automated>for d in py-01-analyze py-03-approved-edit py-04-validation; do (cd tests/eval/matrix/$d/fixture && python3 -m pytest test_calc.py -q) || exit 1; done</automated>
  </verify>
  <done>All three Python shape fixtures exist as flat 3-file repos; pytest passes in each isolated copy; editable add() present; no src/ layout.</done>
</task>

<task type="auto">
  <name>Task 2: Duplicate the three Python-only golden fixtures (py-02, py-05, py-06)</name>
  <files>tests/eval/matrix/py-02-plan-only/fixture/calc.py, tests/eval/matrix/py-05-resume/fixture/notes.txt, tests/eval/matrix/py-06-fetch-summarize/fixture/README.md</files>
  <read_first>
    - tests/eval/golden/02-plan-only/fixture/calc.py (source to copy — bare add() without type hints, the plan-mode edit target)
    - tests/eval/golden/05-resume/fixture/notes.txt (source to copy — Project Meridian status report, the summarize target)
    - tests/eval/golden/06-fetch-summarize/fixture/README.md (source to copy — minimal fetch fixture)
    - E2-RESEARCH.md §Python-Only Cells lines 522-528 + Open Q3 lines 761-764 (duplicate not symlink — copytree handles per-task dirs)
  </read_first>
  <action>
    Copy the three golden fixtures into their matrix homes verbatim (byte-for-byte). Copy `tests/eval/golden/02-plan-only/fixture/calc.py` → `tests/eval/matrix/py-02-plan-only/fixture/calc.py`. Copy `tests/eval/golden/05-resume/fixture/notes.txt` → `tests/eval/matrix/py-05-resume/fixture/notes.txt`. Copy `tests/eval/golden/06-fetch-summarize/fixture/README.md` → `tests/eval/matrix/py-06-fetch-summarize/fixture/README.md`. Do this with `cp` (or Read+Write preserving exact bytes), NOT symlinks (RESEARCH Open Q3 — `shutil.copytree` in `_prepare_fixture` copies per-task-dir; symlinks complicate it). Do not modify content — the matrix task.tomls (plan 05) point at these identical layouts so each matrix cell is self-contained.
  </action>
  <acceptance_criteria>
    - `diff tests/eval/golden/02-plan-only/fixture/calc.py tests/eval/matrix/py-02-plan-only/fixture/calc.py` exits 0 (identical)
    - `diff tests/eval/golden/05-resume/fixture/notes.txt tests/eval/matrix/py-05-resume/fixture/notes.txt` exits 0
    - `diff tests/eval/golden/06-fetch-summarize/fixture/README.md tests/eval/matrix/py-06-fetch-summarize/fixture/README.md` exits 0
    - `test ! -L tests/eval/matrix/py-02-plan-only/fixture/calc.py` (regular file, not a symlink) exits 0
  </acceptance_criteria>
  <verify>
    <automated>diff tests/eval/golden/02-plan-only/fixture/calc.py tests/eval/matrix/py-02-plan-only/fixture/calc.py && diff tests/eval/golden/05-resume/fixture/notes.txt tests/eval/matrix/py-05-resume/fixture/notes.txt && diff tests/eval/golden/06-fetch-summarize/fixture/README.md tests/eval/matrix/py-06-fetch-summarize/fixture/README.md</automated>
  </verify>
  <done>Three Python-only fixtures are byte-identical copies of their golden analogs, as regular files (not symlinks).</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| fixture file → runner's isolated copy | Fixtures are static, committed, developer-authored; copied to a temp dir before any check runs (E1 `_prepare_fixture`) |
| pytest check → fixture copy cwd | `python3 -m pytest` executes ONLY in the isolated copy, never the Voss repo root (E1 `_run_checks` semantics) |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-E2-03 | Tampering | pytest executing arbitrary toolchain code | mitigate | Fixture has zero network/install side effects — only stdlib + the `calc` module; pytest runs in the runner's isolated temp copy, never repo root. |
| T-E2-04 | Tampering | Prompt injection via fixture content | accept | Fixtures are static + committed; no user-supplied content (RESEARCH Security Domain). |
| T-E2-SC | Tampering | pip install in fixture | mitigate | NO `pip install -e .` — flat layout resolves imports at cwd; no package install step (Pitfall 3). |
</threat_model>

<verification>
- All three shape fixtures pass `python3 -m pytest test_calc.py -q` in their isolated dirs.
- The three Python-only fixtures byte-match their golden sources.
- No fixture exceeds the D-01 ≤5-file limit; no src/ layout; no network/install side effects.
</verification>

<success_criteria>
- Six `tests/eval/matrix/py-*/fixture/` dirs exist
- py-01/03/04 are flat 3-file calc repos with editable typed add()
- py-02/05/06 are byte-copies of golden fixtures
- pytest green in each shape fixture; EVGLD-01 Python shape satisfied
</success_criteria>

<output>
Create `.planning/phases/E2-golden-tasks-repo-matrix/E2-02-SUMMARY.md` when done
</output>
