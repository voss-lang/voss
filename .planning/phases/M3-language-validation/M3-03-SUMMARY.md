---
phase: M3
plan: 03
status: complete
date: 2026-05-11
---

# M3-03 Summary — D-07 memory.semantic + memory.working coverage fixtures

## Fixture files

### tests/parser/examples/coverage/memory_semantic.voss (7 LOC)
```
# memory_semantic.voss — D-07 coverage fixture for memory.semantic

let kb: memory.semantic(source: "./knowledge_base/")

fn lookup(q: string) -> list<string> {
    return kb.retrieve(q, top_k: 3)
}
```

### tests/parser/examples/coverage/memory_working.voss (7 LOC)
```
# memory_working.voss — D-07 coverage fixture for memory.working

let scratchpad: memory.working(capacity: 8)

fn note(content: string) {
    scratchpad.add(content)
}
```

## Test functions added

| File | Function | Purpose |
|------|----------|---------|
| `tests/parser/test_examples.py` | `test_coverage_example_parses(name)` | Parametrized over `COVERAGE_NAMES`; asserts `program.body` non-empty |
| `tests/analyzer/test_examples.py` | `test_memory_semantic_coverage_analyzes_clean` | `analyze(emit_indexes=False)` returns `ok=True`, no error-severity diagnostics |
| `tests/analyzer/test_examples.py` | `test_memory_working_coverage_analyzes_clean` | Same shape, working memory |
| `tests/codegen/test_snapshots_coverage.py` | `test_generated_coverage_sources_match_snapshots` | Byte-faithful match against snapshots |
| `tests/codegen/test_snapshots_coverage.py` | `test_coverage_snapshots_are_readable_and_parseable` | `_assert_readable_snapshot` invariants |

## Snapshot files

### tests/codegen/snapshots/coverage/memory_semantic.py (254 bytes, 12 lines)
First import line: `from voss_runtime import SemanticMemory`
Emits `kb = SemanticMemory(source='./knowledge_base/')` inside `async def main()`.

### tests/codegen/snapshots/coverage/memory_working.py (228 bytes, 12 lines)
First import line: `from voss_runtime import WorkingMemory`
Emits `scratchpad = WorkingMemory(capacity=8)` inside `async def main()`.

Both AST-parseable, no compiler imports, single trailing newline, pass `_assert_readable_snapshot`.

## pytest -k coverage selection

```
$ pytest tests/parser/ tests/analyzer/ tests/codegen/ -q -k coverage
......                                                                   [100%]
6 passed
```

- 2 parser (one per fixture, via `test_coverage_example_parses` parametrize)
- 2 analyzer (`test_memory_{semantic,working}_coverage_analyzes_clean`)
- 2 codegen (`test_generated_coverage_sources_match_snapshots`, `test_coverage_snapshots_are_readable_and_parseable`)

## Pre-existing tests — no regression

| Suite | Before | After |
|-------|--------|-------|
| `tests/parser/test_examples.py` | 8 passed | 10 passed (8 original + 2 new coverage) |
| `tests/analyzer/test_examples.py` | 4 passed | 6 passed (4 original + 2 new) |
| `tests/codegen/test_snapshots.py` | 3 passed | 3 passed (unchanged) |
| `tests/codegen/` (full) | 49 passed | 51 passed (+2 new in `test_snapshots_coverage.py`) |

## Carry-forward

- M3-04 lands `memory.episodic` via `samples/support.voss` or `samples/assistant.voss` (per CONTEXT D-07). With these test-only fixtures shipped, LANG-07 coverage matrix is: `episodic` → runnable sample, `semantic` + `working` → test-only fixtures. Any future codegen refactor breaking `SemanticMemory(...)` or `WorkingMemory(...)` lowering shape fails `test_generated_coverage_sources_match_snapshots` immediately.
- `_assert_readable_snapshot` reused via import (not duplicated) — single source of truth for the readability invariant.

## Acceptance criteria — all met

- Fixtures exist with required substrings ✓
- Parser test parametrize via `COVERAGE_NAMES` ✓
- Analyzer test functions defined and pass ✓
- Snapshot files exist, contain `SemanticMemory` / `WorkingMemory` ✓
- New codegen test imports `_assert_readable_snapshot` ✓
- 2 `def test_` in `test_snapshots_coverage.py`; 8 occurrences of `coverage` substring (well above the 3-minimum) ✓
- AST-parseable snapshots ✓
- All suites pass under `-k coverage` selection (6 tests) ✓
