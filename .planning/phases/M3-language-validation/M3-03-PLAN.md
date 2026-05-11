---
phase: M3
plan: 03
type: execute
wave: 0
depends_on: [M1, M2]
files_modified:
  - tests/parser/examples/coverage/memory_semantic.voss
  - tests/parser/examples/coverage/memory_working.voss
  - tests/parser/test_examples.py
  - tests/analyzer/test_examples.py
  - tests/codegen/test_snapshots_coverage.py
  - tests/codegen/snapshots/coverage/memory_semantic.py
  - tests/codegen/snapshots/coverage/memory_working.py
autonomous: true
requirements:
  - LANG-07
  - LANG-08
tags:
  - fixtures
  - coverage
  - parser
  - analyzer
  - codegen

must_haves:
  truths:
    - "tests/parser/examples/coverage/memory_semantic.voss and memory_working.voss exist as self-contained fixtures that parse via the existing parser."
    - "tests/parser/test_examples.py parametrizes over the coverage fixtures and asserts they parse without diagnostics (pytest -k coverage selects them)."
    - "tests/analyzer/test_examples.py adds tests covering memory.semantic + memory.working that exercise emit_indexes=False analyze() and assert no ANLY* diagnostic codes fire (pytest -k coverage selects them)."
    - "tests/codegen/test_snapshots_coverage.py asserts codegen output for both coverage fixtures matches snapshot files AND passes _assert_readable_snapshot (pytest -k coverage selects it)."
    - "Snapshot files under tests/codegen/snapshots/coverage/ are byte-faithful to current codegen output; readability invariants (no compiler imports, no one-liner if/return, no semicolons) hold."
  artifacts:
    - path: "tests/parser/examples/coverage/memory_semantic.voss"
      provides: "self-contained .voss exercising memory.semantic(source: ...)"
      contains: "memory.semantic"
    - path: "tests/parser/examples/coverage/memory_working.voss"
      provides: "self-contained .voss exercising memory.working(capacity: N)"
      contains: "memory.working"
    - path: "tests/parser/test_examples.py"
      provides: "parametrized parse coverage of new fixtures"
      contains: "coverage/memory_semantic"
    - path: "tests/analyzer/test_examples.py"
      provides: "test_memory_semantic_coverage_analyzes_clean + test_memory_working_coverage_analyzes_clean"
      contains: "test_memory_semantic_coverage"
    - path: "tests/codegen/test_snapshots_coverage.py"
      provides: "new file mirroring test_snapshots.py for coverage fixtures; reuses _assert_readable_snapshot via import"
      contains: "_assert_readable_snapshot"
    - path: "tests/codegen/snapshots/coverage/memory_semantic.py"
      provides: "byte-faithful generated Python snapshot for memory_semantic.voss"
      contains: "SemanticMemory"
    - path: "tests/codegen/snapshots/coverage/memory_working.py"
      provides: "byte-faithful generated Python snapshot for memory_working.voss"
      contains: "WorkingMemory"
  key_links:
    - from: "tests/parser/test_examples.py"
      to: "EXAMPLES_DIR/'coverage'/*.voss"
      via: "parametrize over COVERAGE_NAMES tuple holding subdir-prefixed names"
      pattern: "coverage/memory"
    - from: "tests/codegen/test_snapshots_coverage.py"
      to: "tests.codegen.test_snapshots._assert_readable_snapshot"
      via: "module-level import"
      pattern: "from tests.codegen.test_snapshots import _assert_readable_snapshot"
    - from: "tests/analyzer/test_examples.py"
      to: "tests/parser/examples/coverage/memory_{semantic,working}.voss"
      via: "_load helper resolves coverage/memory_semantic.voss relative path"
      pattern: "_load(\"coverage/memory_"
---

<objective>
Land D-07: parser, analyzer, and codegen coverage fixtures for memory.semantic and memory.working. These are test-only fixtures (CONTEXT D-07 explicitly keeps these primitives out of the three runnable samples) that prove the construct survives the parser to analyzer to codegen pipeline. Selected via `pytest -k coverage` per M3-VALIDATION row.

Purpose: LANG-07 requires preservation of all three memory primitives. memory.episodic lands in samples/support.voss (M3-04). The other two need test-only coverage so any future codegen/grammar refactor that breaks them surfaces immediately. Mirrors the existing parser/analyzer/codegen test trio established for the three samples.

Output:
- Two minimal .voss fixtures under tests/parser/examples/coverage/.
- One parametrized addition to tests/parser/test_examples.py covering both fixtures.
- Two new analyzer test functions in tests/analyzer/test_examples.py.
- New file tests/codegen/test_snapshots_coverage.py that imports _assert_readable_snapshot from the existing test_snapshots.py and asserts byte-faithful snapshots for both fixtures.
- Two snapshot files under tests/codegen/snapshots/coverage/.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M3-language-validation/M3-CONTEXT.md
@.planning/phases/M3-language-validation/M3-RESEARCH.md
@.planning/phases/M3-language-validation/M3-PATTERNS.md
@tests/parser/examples/assistant.voss
@tests/parser/test_examples.py
@tests/analyzer/test_examples.py
@tests/codegen/test_snapshots.py
@tests/codegen/test_examples.py

<interfaces>
From tests/parser/test_examples.py:1-24 — adaptation target. Note EXAMPLES_DIR = Path(__file__).parent / "examples"; NAMES tuple parametrizes test_example_parses + test_example_matches_golden. Computes path as EXAMPLES_DIR / f"{name}.voss" — so subdir-prefixed names like "coverage/memory_semantic" resolve to examples/coverage/memory_semantic.voss correctly.

From tests/analyzer/test_examples.py:1-85 — EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "parser" / "examples"; _load(name) helper parses a fixture; tests assert specific diagnostic codes are absent. Pattern: `[d for d in result.diagnostics if d.code == "ANLY001"] == []`.

From tests/codegen/test_snapshots.py — SNAPSHOTS = Path(__file__).resolve().parent / "snapshots" (module-level); _assert_readable_snapshot, _assert_starts_with_imports, _assert_no_compiler_imports are module-level functions and directly importable: `from tests.codegen.test_snapshots import _assert_readable_snapshot`.

From tests/codegen/test_examples.py:23-95 — _compile_example(tmp_path, name, analysis=None) reads tests/parser/examples/{name}.voss, parses, analyzes with FakeIndexBuilder + emit_indexes=False, generates Python. Returns object with .source attribute. Directly importable for snapshot generation in Task 3.

Codegen lowerings (verified via voss_runtime/__init__.py exports + codegen.py:182-186, 690-705):
- memory.semantic(source: "X") -> SemanticMemory(source="X")
- memory.working(capacity: N) -> WorkingMemory(capacity=N)
- memory.episodic(capacity: N turns) -> EpisodicMemory(capacity=N)
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add parser coverage fixtures + parametrize tests/parser/test_examples.py</name>
  <files>tests/parser/examples/coverage/memory_semantic.voss, tests/parser/examples/coverage/memory_working.voss, tests/parser/test_examples.py</files>
  <read_first>
    - tests/parser/test_examples.py (full file — typically <30 LOC; confirm whether test_example_matches_golden reads from a golden directory and whether it skips on missing-golden — guides whether Task 1 needs to create golden JSON)
    - tests/parser/examples/assistant.voss (lines 1-18 — sole in-tree reference for memory.semantic syntax; use as the template for fixture shape)
    - voss/grammar.lark (lines 16-22 for let_stmt + type_expr accepting memory.X(args); line 215 for COMMENT syntax confirming # is accepted)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern: parser/analyzer/codegen coverage fixtures for memory.semantic / memory.working" — exact fixture content to mirror)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/parser/examples/coverage/memory_semantic.voss + memory_working.voss" — adaptation notes; recommendation = option (a) extend NAMES tuple)
  </read_first>
  <behavior>
    - tests/parser/examples/coverage/memory_semantic.voss exists and contains a let declaration of type memory.semantic plus a fn that calls .retrieve on it.
    - tests/parser/examples/coverage/memory_working.voss exists and contains a let declaration of type memory.working plus a fn that calls .add on it.
    - Both fixtures are 5-10 LOC, self-contained: no use imports, no match, no agent, no prompt blocks. Header comment line marks them as D-07 coverage fixtures.
    - tests/parser/test_examples.py adds a COVERAGE_NAMES tuple = ("coverage/memory_semantic", "coverage/memory_working") and adds at least one parametrized test function selected by `pytest -k coverage`.
    - `parse(src, file="memory_semantic.voss")` returns a Program with non-empty .statements list; same for memory_working.voss. Neither raises.
    - The 4 existing parser-golden tests (classify/support/research/assistant) continue to pass unchanged.
  </behavior>
  <action>
    1. Create the directory tests/parser/examples/coverage/ (mkdir).
    2. Create tests/parser/examples/coverage/memory_semantic.voss with 4-space indent matching assistant.voss style. Content (file ends with a single trailing newline):
       Line 1: a hash-prefixed comment naming the fixture and decision: `# memory_semantic.voss — D-07 coverage fixture for memory.semantic`
       Line 2: blank
       Line 3: `let kb: memory.semantic(source: "./knowledge_base/")`
       Line 4: blank
       Line 5: `fn lookup(q: string) -> list<string> {`
       Line 6 (indented 4 spaces): `return kb.retrieve(q, top_k: 3)`
       Line 7: `}`
    3. Create tests/parser/examples/coverage/memory_working.voss with the same shape. Content:
       Line 1: `# memory_working.voss — D-07 coverage fixture for memory.working`
       Line 2: blank
       Line 3: `let scratchpad: memory.working(capacity: 8)`
       Line 4: blank
       Line 5: `fn note(content: string) {`
       Line 6 (indented 4 spaces): `scratchpad.add(content)`
       Line 7: `}`
    4. Open tests/parser/test_examples.py. After the existing NAMES tuple, add a new top-level tuple: `COVERAGE_NAMES = ("coverage/memory_semantic", "coverage/memory_working")`. The subdir-prefix form is intentional — the existing test_example_parses body computes `EXAMPLES_DIR / f"{name}.voss"` which resolves examples/coverage/memory_semantic.voss correctly.
    5. Add a new parametrized test function `test_coverage_example_parses(name)` decorated with `@pytest.mark.parametrize("name", COVERAGE_NAMES)`. Body: read EXAMPLES_DIR / f"{name}.voss" as text, call parse(src, file=f"{name}.voss"), assert the returned Program has a non-empty .statements list (`assert program.statements`).
    6. If the existing test_example_matches_golden reads from examples/golden/ and FAILS (not skips) on missing golden, ALSO add `test_coverage_example_matches_golden` parametrized over COVERAGE_NAMES that decorates with `@pytest.mark.skip(reason="golden snapshot not required for D-07 coverage fixtures")` so the keyword filter `-k coverage` matches but the test does not actually run. If the existing golden test skips on missing files, omit this step.
    7. Do NOT extend the original NAMES tuple. Coverage fixtures stay separate so `pytest -k coverage` selects only the new ones (M3-VALIDATION constraint).
    8. Do NOT add a `use` statement to either fixture — it is unnecessary for memory.X coverage and would entangle this plan with the use-path concerns from Pitfall 1.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/parser/test_examples.py -v -k coverage --no-header 2>&1 | tail -10 && pytest tests/parser/test_examples.py -v --no-header 2>&1 | tail -10 && python -c "from voss import parse; from pathlib import Path; p1 = parse(Path('tests/parser/examples/coverage/memory_semantic.voss').read_text(), file='memory_semantic.voss'); assert p1.statements; p2 = parse(Path('tests/parser/examples/coverage/memory_working.voss').read_text(), file='memory_working.voss'); assert p2.statements"</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/parser/examples/coverage/memory_semantic.voss && test -f tests/parser/examples/coverage/memory_working.voss` exits 0.
    - `grep -c "memory.semantic" tests/parser/examples/coverage/memory_semantic.voss` returns at least 1.
    - `grep -c "memory.working" tests/parser/examples/coverage/memory_working.voss` returns at least 1.
    - `grep -c "COVERAGE_NAMES" tests/parser/test_examples.py` returns at least 1.
    - `grep -c "test_coverage_example_parses" tests/parser/test_examples.py` returns at least 1.
    - `pytest tests/parser/test_examples.py -v -k coverage` reports at least 2 passed (one per fixture).
    - `pytest tests/parser/test_examples.py -v` reports the original 4 names still passing (8 tests minimum across parses+golden parametrizations).
    - `python -c "from voss import parse; from pathlib import Path; p = parse(Path('tests/parser/examples/coverage/memory_semantic.voss').read_text(), file='memory_semantic.voss'); assert p.statements"` exits 0.
  </acceptance_criteria>
  <done>Two coverage fixtures land; parser test parametrizes over them; pytest -k coverage selects them; no existing parser test regresses.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend tests/analyzer/test_examples.py with coverage tests for memory.semantic + memory.working</name>
  <files>tests/analyzer/test_examples.py</files>
  <read_first>
    - tests/analyzer/test_examples.py (full file lines 1-85 — confirm _load helper signature; confirm whether _load accepts subdir-prefixed names like "coverage/memory_semantic.voss" or requires modification)
    - tests/parser/examples/coverage/memory_semantic.voss (created by Task 1)
    - tests/parser/examples/coverage/memory_working.voss (created by Task 1)
    - voss/analyzer.py (lines 166-211 — Analyzer.__init__; FakeIndexBuilder is used in the existing tests to satisfy the index_builder parameter)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/analyzer/examples/coverage/ (NEW) — D-07" — adaptation notes; recommendation = option (a) reuse the parser fixtures from inside analyzer tests by extending the same _load helper)
  </read_first>
  <behavior>
    - Two new test functions in tests/analyzer/test_examples.py: test_memory_semantic_coverage_analyzes_clean and test_memory_working_coverage_analyzes_clean.
    - Each loads its respective coverage fixture via `_load("coverage/memory_semantic.voss")` (or whatever path-resolution _load accepts; modify _load if needed).
    - Each calls `analyze(program, source_path=..., emit_indexes=False, index_builder=FakeIndexBuilder())` (mirroring the existing pattern at line 34-41 + 13-24 of the file).
    - Each asserts `result.ok is True` AND `[d for d in result.diagnostics if d.severity == "error"] == []` (no ERROR-level diagnostics fire).
    - The 4 existing analyzer-example tests (test_classify_..., test_support_..., test_research_..., test_assistant_...) continue to pass unchanged.
    - `pytest tests/analyzer/test_examples.py -k coverage -v` selects exactly the two new tests.
  </behavior>
  <action>
    1. Open tests/analyzer/test_examples.py. Read the existing _load helper (around lines 13-30). If _load already accepts a path-like string with slashes (e.g., already does `(EXAMPLES_DIR / name)` where name is "coverage/memory_semantic.voss"), skip modifying it. If _load assumes a flat filename, modify it to accept either form: build the path as `EXAMPLES_DIR / name` so subdir-prefixed names work.
    2. Below the existing test_assistant_* function, add two new test functions:
       - `def test_memory_semantic_coverage_analyzes_clean()`: program = _load("coverage/memory_semantic.voss"); result = analyze(program, source_path="coverage/memory_semantic.voss", emit_indexes=False, index_builder=FakeIndexBuilder()); `assert result.ok, [d.message for d in result.diagnostics]`; `errors = [d for d in result.diagnostics if str(getattr(d, 'severity', 'error')).lower() == 'error']; assert errors == [], errors` (defensive about whether Diagnostic objects expose a severity attribute — if not, simply assert all diagnostics are non-blocking).
       - `def test_memory_working_coverage_analyzes_clean()`: identical shape, but with "coverage/memory_working.voss".
    3. Confirm FakeIndexBuilder is already imported in the file (existing analyzer tests use it). If not, import from tests.codegen.test_examples or define inline mirroring the codegen helpers shape.
    4. Run `pytest tests/analyzer/test_examples.py -v` — all original tests must still pass.
    5. Do NOT modify the original test bodies. Do NOT add a new EXAMPLES_DIR. Do NOT make these tests depend on the parser or codegen test files at runtime (independent assertions only).
    6. Add a one-line comment above each new test: `# D-07 coverage: memory.semantic (test-only fixture).`
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/analyzer/test_examples.py -v -k coverage --no-header 2>&1 | tail -10 && pytest tests/analyzer/test_examples.py -v --no-header 2>&1 | tail -15</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_memory_semantic_coverage_analyzes_clean" tests/analyzer/test_examples.py` returns 1.
    - `grep -c "def test_memory_working_coverage_analyzes_clean" tests/analyzer/test_examples.py` returns 1.
    - `grep -c "coverage/memory_semantic.voss" tests/analyzer/test_examples.py` returns at least 1.
    - `grep -c "coverage/memory_working.voss" tests/analyzer/test_examples.py` returns at least 1.
    - `pytest tests/analyzer/test_examples.py -v -k coverage` reports 2 passed.
    - `pytest tests/analyzer/test_examples.py -v` reports at least 6 passed (4 existing + 2 new). No new failures.
  </acceptance_criteria>
  <done>Coverage fixtures analyze cleanly; pytest -k coverage routes to them; existing analyzer tests untouched.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Create tests/codegen/test_snapshots_coverage.py + snapshot files for both coverage fixtures</name>
  <files>tests/codegen/test_snapshots_coverage.py, tests/codegen/snapshots/coverage/memory_semantic.py, tests/codegen/snapshots/coverage/memory_working.py</files>
  <read_first>
    - tests/codegen/test_snapshots.py (full file lines 1-85 — mirror the pattern: _generated_sources builds dict, asserts source == snapshot.read_text(), _assert_readable_snapshot enforces invariants)
    - tests/codegen/test_examples.py (lines 23-95 — _compile_example signature; FakeIndexBuilder definition; this task's compile call mirrors test_examples.py:75-93)
    - tests/codegen/snapshots/classify.py (read first 30 lines — confirm expected import header shape: `from voss_runtime import ...` lines come first; this guides the snapshot file template)
    - tests/parser/examples/coverage/memory_semantic.voss (created Task 1 — the source)
    - tests/parser/examples/coverage/memory_working.voss (created Task 1 — the source)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/codegen/snapshots/coverage/ (NEW) — D-07" — adaptation notes; recommendation = new file test_snapshots_coverage.py rather than extending test_snapshots.py, so -k coverage selects it cleanly)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern: parser/analyzer/codegen coverage fixtures" — confirms snapshot path under tests/codegen/snapshots/coverage/)
  </read_first>
  <behavior>
    - tests/codegen/test_snapshots_coverage.py exists and imports _assert_readable_snapshot from tests.codegen.test_snapshots.
    - It defines a _generated_coverage_sources(tmp_path) helper that calls _compile_example(tmp_path, "coverage/memory_semantic") and _compile_example(tmp_path, "coverage/memory_working"), returning {name: source}.
    - It defines test_generated_coverage_sources_match_snapshots(tmp_path) that loops over the dict and asserts source == (SNAPSHOTS_COVERAGE / f"{name_basename}.py").read_text().
    - It defines test_coverage_snapshots_are_readable_and_parseable() that loops over the two snapshot files and calls _assert_readable_snapshot.
    - Snapshot files exist under tests/codegen/snapshots/coverage/ and are byte-faithful to the current codegen output. Each starts with `from voss_runtime import ...` (no compiler imports), ends with a single trailing newline, and is parseable by ast.parse.
    - `pytest tests/codegen/test_snapshots_coverage.py -v -k coverage` selects both new test functions.
  </behavior>
  <action>
    1. Create directory tests/codegen/snapshots/coverage/.
    2. Generate the snapshot content by running this inline command (after Tasks 1 + 2 are complete) — write to a temp file, inspect, then save into snapshots/coverage/:
       `python -c "from tests.codegen.test_examples import _compile_example; import tempfile, pathlib; t = pathlib.Path(tempfile.mkdtemp()); r1 = _compile_example(t, 'coverage/memory_semantic'); print('---semantic---'); print(r1.source); r2 = _compile_example(t, 'coverage/memory_working'); print('---working---'); print(r2.source)"`
       Capture the two outputs verbatim into:
       - tests/codegen/snapshots/coverage/memory_semantic.py
       - tests/codegen/snapshots/coverage/memory_working.py
       Each ends with exactly one trailing newline. Do NOT hand-edit the content; codegen output is authoritative.
    3. Also confirm _compile_example accepts subdir-prefixed names. The existing `_read_example(f"{name}.voss")` constructs EXAMPLES / f"{name}.voss" which resolves "coverage/memory_semantic.voss" against tests/parser/examples/ correctly. If _read_example asserts the file exists with a phase-4 message at test_examples.py:69, the assertion will pass because the fixture exists.
    4. Create tests/codegen/test_snapshots_coverage.py with this structure:
       - Module docstring naming D-07.
       - Imports: `from __future__ import annotations`, `from pathlib import Path`, `import pytest`, `from tests.codegen.test_examples import _compile_example`, `from tests.codegen.test_snapshots import _assert_readable_snapshot`.
       - Module-level constant: `SNAPSHOTS_COVERAGE = Path(__file__).resolve().parent / "snapshots" / "coverage"`.
       - Module-level constant: `COVERAGE_NAMES = ("memory_semantic", "memory_working")`.
       - Helper `_generated_coverage_sources(tmp_path)`: returns `{name: _compile_example(tmp_path, f"coverage/{name}").source for name in COVERAGE_NAMES}`.
       - `def test_generated_coverage_sources_match_snapshots(tmp_path):`: `generated = _generated_coverage_sources(tmp_path); for name, source in generated.items(): snapshot = (SNAPSHOTS_COVERAGE / f"{name}.py").read_text(); assert source == snapshot, f"snapshot drift in coverage/{name}.py"`.
       - `def test_coverage_snapshots_are_readable_and_parseable():`: `for name in COVERAGE_NAMES: snapshot = (SNAPSHOTS_COVERAGE / f"{name}.py").read_text(); _assert_readable_snapshot(name, snapshot)`.
       - Both test names contain the substring "coverage" so pytest -k coverage selects them.
    5. Run `pytest tests/codegen/test_snapshots_coverage.py -v` and confirm both tests pass. If `test_generated_coverage_sources_match_snapshots` fails on first run, the captured snapshot in step 2 was wrong — regenerate from the FRESH codegen output and overwrite the snapshot files.
    6. Do NOT extend tests/codegen/test_snapshots.py. New file isolates -k coverage selection and avoids touching the existing well-tested file.
    7. Do NOT add the coverage names to `test_generated_example_sources_match_snapshots` in test_snapshots.py — keep separate.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/codegen/test_snapshots_coverage.py -v --no-header 2>&1 | tail -10 && pytest tests/codegen/ -v -k coverage --no-header 2>&1 | tail -10 && pytest tests/codegen/test_snapshots.py -v --no-header 2>&1 | tail -10</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/codegen/test_snapshots_coverage.py` exits 0.
    - `test -f tests/codegen/snapshots/coverage/memory_semantic.py && test -f tests/codegen/snapshots/coverage/memory_working.py` exits 0.
    - `grep -c "SemanticMemory" tests/codegen/snapshots/coverage/memory_semantic.py` returns at least 1.
    - `grep -c "WorkingMemory" tests/codegen/snapshots/coverage/memory_working.py` returns at least 1.
    - `grep -c "from tests.codegen.test_snapshots import _assert_readable_snapshot" tests/codegen/test_snapshots_coverage.py` returns 1.
    - `grep -c "^def test_" tests/codegen/test_snapshots_coverage.py` returns 2 (match-snapshots + readable).
    - `grep -c "coverage" tests/codegen/test_snapshots_coverage.py` returns at least 3 (function names + paths + module constants — guarantees -k coverage selection).
    - `pytest tests/codegen/test_snapshots_coverage.py -v` reports 2 passed.
    - `pytest tests/codegen/ -v -k coverage` reports at least 2 passed.
    - `pytest tests/codegen/test_snapshots.py -v` still reports the existing tests passing (no regression).
    - `python -c "import ast; ast.parse(open('tests/codegen/snapshots/coverage/memory_semantic.py').read())"` exits 0.
    - `python -c "import ast; ast.parse(open('tests/codegen/snapshots/coverage/memory_working.py').read())"` exits 0.
  </acceptance_criteria>
  <done>Codegen snapshot coverage exists; readability invariants enforced; pytest -k coverage routes to it; no existing codegen test regresses.</done>
</task>

</tasks>

<verification>
- `pytest tests/parser/test_examples.py tests/analyzer/test_examples.py tests/codegen/test_snapshots_coverage.py tests/codegen/test_snapshots.py -q -k "coverage or (classify or support or research or assistant)" --no-header 2>&1 | tail -10` exits 0 (catches both new tests and confirms existing pattern still passes).
- `pytest tests/codegen/ -q --no-header 2>&1 | tail -10` exits 0 (full codegen suite, including unrelated tests).
- `pytest tests/parser/ tests/analyzer/ tests/codegen/ -q -k coverage --no-header 2>&1 | tail -10` exits 0 with at least 6 tests selected (2 parser + 2 analyzer + 2 codegen).
</verification>

<success_criteria>
- LANG-07 fully covered: memory.episodic via samples (M3-04), memory.semantic + memory.working via these test-only fixtures.
- pytest -k coverage selects exactly the new D-07 fixtures across all three suites.
- Snapshot files are byte-faithful; readability invariants enforced via shared _assert_readable_snapshot.
- Existing 4-sample parser/analyzer/codegen tests are unaffected.
- New file structure mirrors the established pattern: parser fixture → analyzer test → codegen snapshot.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| .voss source → codegen → .py snapshot | New fixture content crosses three compilation tiers; any drift in any tier is caught by the matching test. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M3-10 | Tampering | A future codegen refactor changes the emitted SemanticMemory/WorkingMemory line shape, silently breaking memory.X primitives | mitigate | Byte-faithful snapshot tests under tests/codegen/snapshots/coverage/ catch any diff; _assert_readable_snapshot enforces no compiler imports leak. |
| T-M3-11 | Information Disclosure | A snapshot file contains a path leak (developer's tmp_path appears in generated source) | mitigate | _compile_example uses tmp_path passed by the test fixture; codegen's _resolve_cache_root (codegen.py:218-235) already normalizes paths to relative cache forms. Snapshot diff will catch any absolute-path leak. |
| T-M3-12 | Repudiation | pytest -k coverage matches an unrelated test (e.g., "discovery" or "recover") and silently runs the wrong assertions | mitigate | All three test files use the literal substring "coverage" in function names + module constants. Acceptance criteria grep enforces. Existing tests do not contain "coverage" in their names. |
</threat_model>

<output>
After completion, create `.planning/phases/M3-language-validation/M3-03-SUMMARY.md` documenting: (1) the two fixture files with their exact content + LOC count, (2) the new test function names in each test file, (3) the snapshot file paths and their first import line, (4) the pytest -k coverage selection count across the three suites, (5) confirmation that pre-existing parser/analyzer/codegen tests pass unchanged (paste the pre + post pytest output count).
</output>
