# Phase 03 - Pattern Map

**Phase:** Semantic Analysis
**Date:** 2026-05-07
**Owner:** GSD pattern mapper

## Boundary Assumptions

- Phase 2 parser package files are planned but not present in the current tree.
- Treat `voss/ast_nodes.py`, `voss/parser.py`, `voss/transformer.py`, and parser fixtures as incoming contracts, not current source.
- Do not modify runtime analogs unless execution proves a contract mismatch. In particular, preserve the existing `voss_runtime/semantic.py` index/case behavior.
- Phase 3 should walk frozen AST dataclasses without mutation and return analyzer-owned diagnostics, semantic state, and emitted index metadata.

## Likely File Map

| File | Action | Role | Data Flow | Closest Analogs | Executor Patterns |
|------|--------|------|-----------|-----------------|-------------------|
| `voss/analyzer.py` | create | Main semantic pass | `Program` AST -> scope/type state -> `AnalysisResult`; optionally writes `.voss-cache/<program>.idx` | `voss_runtime/context.py`, `voss_runtime/probable.py`, `voss_runtime/semantic.py` | Keep one public `analyze(program, *, source_path=None, cache_dir=".voss-cache", emit_indexes=True, token_estimator=None, index_builder=None)`. Use a small `Analyzer` class with lexical scopes; no external visitor framework or broad type engine. |
| `voss/diagnostics.py` | create | Compile-time diagnostic/result dataclasses | analyzer warnings/errors -> CLI/codegen-readable result | `voss_runtime/exceptions.py`; planned `VossParseError` shape from Phase 2 | Use frozen dataclasses and stable string formatting. Keep diagnostics as data, not raised exceptions, for ANLY warnings. Include `severity`, `code`, `message`, `span`, `hint`. |
| `voss/types.py` or analyzer-local type section | create only if needed | Minimal internal semantic type model | `TypeRef` AST -> `VossType` -> assignment/return/call checks | `ProbableValue[T]` in `voss_runtime/probable.py` | Prefer private classes inside `analyzer.py` until duplication justifies a module. Model only primitives, named types, lists/dicts, `ProbableType`, memory types, and unknown. Unknown suppresses cascading warnings. |
| `voss/__init__.py` | modify after Phase 2 creates package | Public compiler API exports | package import -> `parse`, `analyze`, diagnostics | `voss_runtime/__init__.py` | Re-export only stable public names: `analyze`, `AnalysisResult`, `Diagnostic`, maybe `DiagnosticSeverity`. Keep runtime package separate. |
| `voss/ast_nodes.py` | read-only dependency | AST contract consumed by analyzer | parser output -> analyzer input | Phase 2 planned AST docs | Do not mutate nodes or add analyzer state to them. Use spans from unsafe expression/block nodes for diagnostics. |
| `.voss-cache/<program>.idx` | generated artifact | Compile-time semantic-match manifest | `MatchStmt` similar cases -> embeddings/index JSON -> Phase 4/runtime lookup | `SemanticMatcher.to_index()` and `tests/test_semantic_matcher.py` | Emit atomically inside `cache_dir`; keep paths constrained under `.voss-cache`. Preserve runtime case schema `{label, description, embedding}` inside a program manifest. |
| `tests/analyzer/test_diagnostics.py` | create | Diagnostic/result contract tests | direct AST fixtures -> formatted diagnostics | runtime tests use direct object assertions | Assert severity/code/span/message/hint and stable formatting. Use synthetic/direct AST nodes until parser lands. |
| `tests/analyzer/test_probable.py` | create | ANLY-01 tests | probable declarations/gates -> warnings/no warnings | `tests/test_probable.py` | Cover assignment, return, known-parameter call, `.value` outside gate, `.value` inside `>=` gate, else-branch remains unsafe. |
| `tests/analyzer/test_ctx_budget.py` | create | ANLY-02 tests | `CtxBlock` literals/includes -> token estimate diagnostics | `tests/test_context.py` | Keep estimator deterministic and provider-free. Unknown dynamic values should not warn. |
| `tests/analyzer/test_match_index.py` | create | ANLY-03 tests | match similar cases -> cache manifest | `tests/test_semantic_matcher.py` | Use fake embeddings/index builder by default. Real sentence-transformers coverage should be marked `live` or `slow`, not required for default pytest. |
| `tests/analyzer/test_examples.py` | create later | Parser/analyzer integration | real `.voss` examples -> parse -> analyze | Phase 2 `tests/parser/test_examples.py` plan | Add only after Phase 2 parser fixtures exist. It should verify PRD examples and analyzer quiet/warning expectations. |
| `pyproject.toml` | maybe modify | Package/test config | package discovery and markers | current config packages only `voss_runtime`; markers include `live`, `slow` | When `voss/` exists, update package discovery/source coverage deliberately. Add no new test marker unless needed. |

## Analyzer Data Flow

1. **Predeclare symbols:** collect top-level class names, function/agent signatures, and typed top-level lets from `Program`.
2. **Walk statements in order:** maintain lexical scope stack plus current function return type and ctx state.
3. **Infer expressions shallowly:** literals, identifiers, member access, calls with known signatures, and annotated lets are enough for v1.
4. **Check expected vs actual types:** emit `ANLY001` when `ProbableType(T)` flows into expected `T` without a branch-local confidence gate.
5. **Estimate ctx budgets:** sum only statically known literals/includes/prompts; emit `ANLY002` only when estimate exceeds declared token budget.
6. **Collect similar cases:** each `MatchStmt` with `SimilarPattern` cases becomes one manifest match entry; emit `ANLY003` metadata via `AnalysisResult.indexes`.

## Concrete Patterns To Follow

### Diagnostics

- Mirror Phase 2 parse-error ergonomics, but keep analyzer warnings as returned data.
- Diagnostic spans should point to the smallest unsafe expression: `Identifier`, `Member(..., "value")`, returned value, call argument, or `CtxBlock`.
- Use stable codes:
  - `ANLY001` unguarded `probable<T>` use.
  - `ANLY002` ctx static token estimate exceeds declared budget.
  - `ANLY003` index emission failure or unsafe cache path, if represented diagnostically.
- Do not raise for ordinary warnings. Reserve exceptions for programmer errors or impossible internal states.

### Probable Narrowing

- Normalize `TypeRef(name=QualName(("probable",)), generics=(T,))` into `ProbableType(T)`.
- `if intent @ p >= 0.80 { ... }` narrows `intent` only in the then branch.
- `if intent @ p > 0.80 { ... }` follows the same then-branch rule.
- `<` and `<=` may narrow the else branch if implemented, but v1 can omit that until tests require it.
- `.value` outside a gate should still warn; explicit field access is not the same as confidence validation.
- Unknown types should not produce probable warnings.

### Token Budget Estimation

- Static estimator must not call `ModelProvider`, LiteLLM, OpenAI, Anthropic, or runtime provider token counters.
- Default heuristic can be local: string `max(1, len(text) // 4)`, numeric/bool/null `1`, list/dict sum plus overhead, string concat sum, unknown call `0`.
- Track estimated sizes for `let` bindings when initializers are statically estimable.
- In `CtxBlock`, sum `include` values and literal `ask(...)` prompts. Runtime `ContextScope` remains authoritative.

### Similar Index Emission

- Reuse `voss_runtime.semantic.SemanticMatcher` behavior for case embedding and case schema.
- Keep default tests hermetic by injecting fake embeddings or an index-builder seam. Follow `tests/test_semantic_matcher.py`, where synthetic embeddings avoid model download.
- Manifest recommendation for `.voss-cache/<program>.idx`:

```json
{
  "version": 1,
  "program": "program",
  "model": "sentence-transformers/all-MiniLM-L6-v2",
  "matches": [
    {
      "match_id": "match_12_5",
      "threshold": 0.75,
      "cases": [
        {"label": "case_0", "description": "...", "embedding": [0.0]}
      ]
    }
  ]
}
```

- Use `match_<line_start>_<col_start>` for stable match IDs and ordinal labels unless Phase 4 defines a stronger label contract.
- Write indexes atomically and ensure resolved output stays inside `cache_dir`.

## Test Patterns

- Put analyzer tests under `tests/analyzer/` rather than mixing with runtime tests.
- Start with direct AST fixture construction because Phase 2 is not present yet.
- Convert or add parser-backed fixtures after Phase 2 lands.
- Default verification target: `pytest tests/analyzer -q`.
- Wave/full verification target after parser exists: `pytest tests/parser tests/analyzer -q`.
- Keep real embedding/model tests marked `live` or `slow`; current `pyproject.toml` already defines both markers.

## Non-Goals

- No general-purpose type checker.
- No AST rewrites or analyzer metadata attached to AST nodes.
- No provider-specific token accounting in the compiler.
- No runtime schema churn in `voss_runtime/semantic.py`.
- No parser implementation work in Phase 3 except integration fixes forced by real AST contract mismatches.

## Executor Checklist

- [ ] Confirm Phase 2 files exist before importing `voss.ast_nodes`.
- [ ] Add diagnostics/result types first.
- [ ] Implement type normalization and scope tracking before warning rules.
- [ ] Add ANLY-01 tests before implementing confidence narrowing.
- [ ] Add deterministic ANLY-02 tests before estimator logic.
- [ ] Add fakeable ANLY-03 index tests before real embedding integration.
- [ ] Run `pytest tests/analyzer -q`, then `pytest tests/parser tests/analyzer -q` once parser tests exist.
