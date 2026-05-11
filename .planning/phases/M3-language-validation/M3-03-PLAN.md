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
      provides: "parametrized parse + golden coverage of new fixtures"
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
      via: "parametrize over NAMES + COVERAGE_NAMES; matching golden under examples/golden/coverage/"
      pattern: "coverage/memory"
    - from: "tests/codegen/test_snapshots_coverage.py"
      to: "tests.codegen.test_snapshots._assert_readable_snapshot"
      via: "module-level import"
      pattern: "from tests.codegen.test_snapshots import _assert_readable_snapshot"
    - from: "tests/analyzer/test_examples.py"
      to: "tests/parser/examples/coverage/memory_{semantic,working}.voss"
      via: "_load helper resolves 'coverage/memory_semantic.voss' relative path"
      pattern: "_load(\"coverage/memory_"
---

<objective>
Land D-07: parser, analyzer, and codegen coverage fixtures for `memory.semantic` and `memory.working`. These are test-only fixtures (CONTEXT D-07 explicitly keeps these primitives out of the three runnable samples) that prove the construct survives the parser → analyzer → codegen pipeline. Selected via `pytest -k coverage` per M3-VALIDATION row.

Purpose: LANG-07 requires preservation of all three memory primitives. `memory.episodic` lands in `samples/support.voss` (M3-04). The other two need test-only coverage so any future codegen/grammar refactor that breaks them surfaces immediately. Mirrors the existing parser/analyzer/codegen test trio established for the three samples (parser golden, analyzer no-warn, codegen snapshot+readability).

Output:
- Two minimal `.voss` fixtures under `tests/parser/examples/coverage/`.
- One parametrized addition to `tests/parser/test_examples.py` covering both fixtures (golden file optional — see Task 1).
- Two new analyzer test functions in `tests/analyzer/test_examples.py`.
- New file `tests/codegen/test_snapshots_coverage.py` that imports `_assert_readable_snapshot` from the existing `test_snapshots.py` and asserts byte-faithful snapshots for both fixtures.
- Two snapshot files under `tests/codegen/snapshots/coverage/`.
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
From tests/parser/examples/assistant.voss:1-18 (canonical reference for memory.* + use syntax):

```
let history: memory.episodic(capacity: 20 turns)
let kb: memory.semantic(source: "./knowledge_base/")
use voss.tools as tools
fn chat(userMessage: string) -> string { ... history.add(...) ... kb.retrieve(...) ... }
```

From tests/parser/test_examples.py:1-24 (test scaffold — adaptation target):

```
EXAMPLES_DIR = Path(__file__).parent / "examples"
NAMES = ("classify", "support", "research", "assistant")

@pytest.mark.parametrize("name", NAMES)
def test_example_parses(name):
    src = (EXAMPLES_DIR / f"{name}.voss").read_text()
    ...

@pytest.mark.parametrize("name", NAMES)
def test_example_matches_golden(name):
    # compares against examples/golden/{name}.json or similar — confirm exact mechanism
```

From tests/analyzer/test_examples.py:1-85 (scaffold for new tests):

```
EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "parser" / "examples"

def _load(name: str):
    # parses tests/parser/examples/{name} (supports "subdir/name" too) and returns Program

def test_classify_example_analyzes_without_probable_warning():
    program = _load("classify.voss")
    result = analyze(program, emit_indexes=False, index_builder=FakeIndexBuilder())
    assert [d for d in result.diagnostics if d.code == "ANLY001"] == []
```

From tests/codegen/test_snapshots.py:11-71 (the SNAPSHOTS constant and `_assert_readable_snapshot` are at module scope — directly importable):

```
SNAPSHOTS = Path(__file__).resolve().parent / "snapshots"

def _assert_readable_snapshot(name: str, source: str) -> None:
    ast.parse(source, filename=f"{name}.py")
    _assert_starts_with_imports(source)
    assert ";" not in source
    ...
```

From tests/codegen/test_examples.py:23-95 (FakeIndexBuilder + _compile_example — directly importable):

```
EXAMPLES = Path(__file__).resolve().parents[1] / "parser" / "examples"

class FakeIndexBuilder:
    model = "fake-embedding-model"
    def build_cases(self, cases): ...

def _compile_example(tmp_path: Path, name: str, *, analysis=None):
    source = _read_example(f"{name}.voss")
    program = parse(source, file=f"{name}.voss")
    if analysis is None:
        analysis = analyze(program, source_path=f"{name}.voss", project_root=tmp_path,
                           cache_dir=".voss-cache", emit_indexes=False, index_builder=FakeIndexBuilder())
    return generate_python(program, source_path=f"{name}.voss", analysis=analysis,
                           cache_dir=tmp_path / ".voss-cache", project_root=tmp_path)
```

Codegen lowerings (verified per RESEARCH §"Don't Hand-Roll"):
- `memory.semantic(source: "X")` → `SemanticMemory(source="X")` from voss_runtime
- `memory.working(capacity: N)` → `WorkingMemory(capacity=N)` from voss_runtime
- `memory.episodic(capacity: N turns)` → `EpisodicMemory(capacity=N)` from voss_runtime
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add parser coverage fixtures for memory.semantic and memory.working + parametrize tests/parser/test_examples.py</name>
  <files>tests/parser/examples/coverage/memory_semantic.voss, tests/parser/examples/coverage/memory_working.voss, tests/parser/test_examples.py</files>
  <read_first>
    - tests/parser/test_examples.py (lines 1-24 — full file; confirm whether `test_example_matches_golden` reads from `examples/golden/` or somewhere else; if golden files exist they will need coverage versions, if not skip)
    - tests/parser/examples/assistant.voss (lines 1-18 — sole in-tree reference for memory.semantic syntax)
    - voss/grammar.lark (lines 16-22 — `let_stmt` and `type_expr` rules that accept `memory.X(args)`; lines 215 for COMMENT syntax)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pattern: parser/analyzer/codegen coverage fixtures" — exact fixture content; §"Pitfall 1" — `use` syntax constraints, applies only if fixtures use `use`)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/parser/examples/coverage/memory_semantic.voss + memory_working.voss" — adaptation notes; recommendation: extend the NAMES tuple option (a))
  </read_first>
  <behavior>
    - tests/parser/examples/coverage/memory_semantic.voss exists with content matching the RESEARCH/PATTERNS reference: a `let kb: memory.semantic(source: "./knowledge_base/")` declaration plus a `fn lookup` that calls `kb.retrieve(q, top_k: 3)`.
    - tests/parser/examples/coverage/memory_working.voss exists with content: a `let scratchpad: memory.working(capacity: 8)` declaration plus a `fn note` that calls `scratchpad.add(content)`.
    - Both fixtures are <= 10 LOC and self-contained (no `use` imports, no external `match`, no agent decl) — minimum surface to exercise the construct.
    - tests/parser/test_examples.py extends `NAMES` (or adds a parallel `COVERAGE_NAMES`) such that `pytest tests/parser/test_examples.py -k coverage` selects exactly the two new fixtures.
    - Both new fixtures parse via `parse(src, file=...)` without raising and without emitting parser diagnostics.
    - The 4 existing parser-golden tests (classify/support/research/assistant) continue to pass unchanged.
  </behavior>
  <action>
    1. Create tests/parser/examples/coverage/memory_semantic.voss with this content (text-faithful; replace `<TAB>` notation with literal indentation matching the existing `assistant.voss` style — 4-space indent):
       ```
       # memory_semantic.voss — D-07 coverage fixture for memory.semantic
       let kb: memory.semantic(source: "./knowledge_base/")
       fn lookup(q: string) -> list<string> {
           return kb.retrieve(q, top_k: 3)
       }
       ```
       (Header is a `#` comment — grammar.lark:215 accepts. File ends with a single trailing newline.)
    2. Create tests/parser/examples/coverage/memory_working.voss:
       ```
       # memory_working.voss — D-07 coverage fixture for memory.working
       let scratchpad: memory.working(capacity: 8)
       fn note(content: string) {
           scratchpad.add(content)
       }
       ```
       (Single trailing newline.)
    3. Open tests/parser/test_examples.py. After the `NAMES = ("classify", "support", "research", "assistant")` line at line 8, add: `COVERAGE_NAMES = ("coverage/memory_semantic", "coverage/memory_working")`. The path-with-slash form is intentional: the existing `test_example_parses` body computes `EXAMPLES_DIR / f"{name}.voss"`, which resolves `examples/coverage/memory_semantic.voss` correctly.
    4. Add two new parametrized test functions parallel to the existing ones — name them `test_coverage_example_parses` (parametrize over COVERAGE_NAMES) and `test_coverage_example_matches_golden` (parametrize over COVERAGE_NAMES). Body of `test_coverage_example_parses`: identical to `test_example_parses` (read file, call `parse`, assert no error). Body of `test_coverage_example_matches_golden`: IF the existing `test_example_matches_golden` body reads from `examples/golden/{name}.json` and skips when missing, mirror that with `pytest.skip(...)` on missing golden — coverage fixtures do NOT require golden files in this plan (snapshot coverage is owned by Task 3, golden JSON is a parser-AST snapshot which is out of M3 scope). Concretely: the new function asserts that `(EXAMPLES_DIR / f"{name}.voss").exists()` and `parse(src).statements` is non-empty; that's the keyword-matchable proof.
    5. Run `pytest tests/parser/test_examples.py -k coverage -v` — both new tests must pass. Run `pytest tests/parser/test_examples.py -v` — all original tests must also still pass.
    6. Do NOT add the coverage names to the original `NAMES` tuple — keep separate so `pytest -k coverage` selects only the new ones (per M3-VALIDATION row `coverage-fixtures-parser`).
    7. Do NOT add golden JSON files for the coverage fixtures unless `test_example_matches_golden` raises an unskipped failure when the golden file is missing — in that case, generate a placeholder golden file via the existing test infrastructure rather than asserting on content.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && pytest tests/parser/test_examples.py -v --no-header 2>&1 | tail -20 && python -c "from voss import parse; from pathlib import Path; src1 = Path('tests/parser/examples/coverage/memory_semantic.voss').read_text(); p1 = parse(src1, file='memory_semantic.voss'); assert p1.statements; src2 = Path('tests/parser/examples/coverage/memory_working.voss').read_text(); p2 = parse(src2, file='memory_working.voss'); assert p2.statements"