# Phase 3: Semantic Analysis - Research

**Date:** 2026-05-07
**Phase:** 03-semantic-analysis
**Objective:** Identify what the planner needs to know before implementing ANLY-01, ANLY-02, and ANLY-03.

## Context Summary

Phase 3 is the first compiler phase after parsing. It should consume the frozen dataclass AST planned in Phase 2, walk it without mutating it, and produce:

- Structured diagnostics with file/line/column spans.
- A lightweight semantic model sufficient for confidence-gate warnings.
- Static token-budget warnings for `ctx` blocks.
- Compile-time semantic-match indexes under `.voss-cache/`.

Assumptions for planning:

- Phase 2 has not landed in the current tree yet. There is no `voss/` parser package today; Phase 3 depends on the Phase 2 AST contract in `.planning/phases/02-parser-grammar/02-RESEARCH.md` and plans `02-01` through `02-05`.
- Phase 1 runtime work is partially present in `voss_runtime/`. The semantic matcher index format is already implemented and should be treated as the Phase 3 index contract.
- Graphify was attempted before this research and failed because `graphify-out/graph.json` does not exist, so this research uses planning docs plus source inspection.

## Current Relevant Code Structure

Runtime package files already relevant to Phase 3:

- `voss_runtime/probable.py`
  - `ProbableValue[T]` with `value`, `confidence`, `gate(threshold)`, `unwrap(threshold)`, and `__matmul__(threshold)`.
  - Analyzer should mirror this runtime distinction: a `probable<T>` is not assignable to `T` unless the value is narrowed by a confidence gate or `.value` is accessed inside a gated branch.
- `voss_runtime/context.py`
  - `ContextScope(token_budget, model=None, provider=None, compressor=...)`.
  - `add(content, compression="summarize")`, `ask(prompt, return_type=None)`, and `assemble()`.
  - Analyzer budget estimates should be conservative warnings only; runtime still enforces the hard limit.
- `voss_runtime/budget.py`
  - `BudgetScope(token_limit=None, latency_ms=None, cost_usd=None)` and `run_with_budget(...)`.
  - Mostly Phase 4 codegen input; Phase 3 only validates `within budget(...)` shapes if the AST exposes them.
- `voss_runtime/semantic.py`
  - `DEFAULT_LOCAL_MODEL = "sentence-transformers/all-MiniLM-L6-v2"`.
  - `Case(label, description)`.
  - `SemanticMatcher(cases, threshold=0.75, model=DEFAULT_LOCAL_MODEL, embeddings=None)`.
  - `SemanticMatcher.to_index()` returns JSON-compatible `{model, threshold, cases:[{label, description, embedding}]}`.
  - `SemanticMatcher.write_index(path)` writes the current index format.
  - `SemanticMatcher.from_index(path)` loads without instantiating the encoder.
- `voss_runtime/providers/base.py`
  - `ModelProvider.count_tokens(text, model)` is the runtime token-counting seam.
  - Do not use provider APIs in Phase 3 unless a test injects a trivial estimator; compiler checks must stay local and deterministic.

Planned compiler package files likely touched by Phase 3, after Phase 2 lands:

- `voss/ast_nodes.py`
  - Read-only dependency. Analyzer consumes `Program`, `Span`, `TypeRef`, `LetStmt`, `IfStmt`, `ConfidenceGate`, `CtxBlock`, `IncludeStmt`, `YieldStmt`, `MatchStmt`, `MatchCase`, `SimilarPattern`, `FnDecl`, `AgentDecl`, `ClassDecl`, and related expression nodes.
- `voss/analyzer.py`
  - New main module. Recommended public entry: `analyze(program, *, source_path=None, cache_dir=".voss-cache", emit_indexes=True, token_estimator=None) -> AnalysisResult`.
- `voss/diagnostics.py` or `voss/exceptions.py`
  - Add compile-time diagnostic dataclasses near `VossParseError`. Keep diagnostics separate from runtime exceptions.
- `voss/__init__.py`
  - Re-export `analyze`, `AnalysisResult`, `Diagnostic`, and likely diagnostic severity enum.
- `tests/analyzer/`
  - New focused unit tests for diagnostics, type narrowing, token estimates, and index emission.
- `tests/parser/examples/`
  - Phase 2 examples should become analyzer fixtures once parser goldens exist.

Do not touch in Phase 3 unless tests prove a contract mismatch:

- `voss_runtime/semantic.py` index schema.
- `voss_runtime/probable.py` confidence API.
- `voss_runtime/context.py` runtime compression behavior.

## Existing Parser/AST Contracts To Respect

From Phase 2 planning:

- Every AST node is `@dataclass(frozen=True, slots=True)`.
- Every node carries `span: Span(file, line_start, col_start, line_end, col_end, synthetic=False)`.
- `ConfidenceGate` is not a general expression. It appears only in `IfStmt.condition` and has `target: Expr`, `op: str`, `threshold: float`.
- `LetStmt` has `name`, optional `type_annot`, and optional `value`.
- `TypeRef` is the only concrete `TypeExpr`; it has `name: QualName`, `generics`, and `kwargs`.
- `probable<T>` is represented as `TypeRef(name=QualName(("probable",)), generics=(T,))`.
- `CtxBlock` has a single `BudgetArg` for `ctx(budget: 4000 tokens)`.
- `WithinFallback` has `budget_args`, `primary`, and optional `fallback`.
- `MatchStmt` has `scrutinee`, `cases`, and `threshold`. `@match_threshold(...)` is lifted into `MatchStmt.threshold`.
- `SimilarPattern` stores only the source string text. Phase 3 must assign stable case labels for the index.
- `UseStmt` is parse-only in Phase 2; module resolution is not a Phase 3 requirement.

The analyzer should walk these nodes structurally and never rewrite them. Any inferred type/narrowing state belongs in analyzer-local scopes.

## Standard Stack

Use the project stack already chosen:

- Python 3.11+.
- Dataclasses for diagnostics/results.
- AST walking with plain recursive functions or a small visitor class. No external visitor framework.
- `sentence-transformers` through `voss_runtime.semantic.SemanticMatcher` for compile-time embeddings.
- JSON index files via `SemanticMatcher.write_index()`.
- `pytest` plus temporary directories for cache emission tests.

Do not introduce mypy, pyright, Pydantic, or a full Hindley-Milner engine for Phase 3. The semantic surface is intentionally narrow.

## Architecture Patterns

Recommended module shape:

- `Diagnostic`
  - `severity: Literal["warning", "error"]`
  - `code: str` such as `ANLY001`, `ANLY002`, `ANLY003`
  - `message: str`
  - `span: Span`
  - optional `hint: str | None`
- `AnalysisResult`
  - `diagnostics: tuple[Diagnostic, ...]`
  - `indexes: tuple[EmittedIndex, ...]`
  - helper properties `warnings`, `errors`, `ok`.
- `EmittedIndex`
  - `match_id: str`
  - `path: Path`
  - `case_count: int`
  - `threshold: float`
  - `model: str`
- `Analyzer`
  - Holds lexical scopes, function signatures, class names, and current ctx/gate state.
  - Public method `analyze_program(program) -> AnalysisResult`.

Keep the first implementation single-pass plus small predeclaration setup:

1. Predeclare top-level `class`, `fn`, `agent`, and top-level `let` names when type annotations are available.
2. Walk statements in order with lexical scope stack.
3. For each expression, return an inferred `VossType`.
4. Emit diagnostics when a context expects one type and receives incompatible `probable<T>`.
5. Emit cache indexes when visiting `MatchStmt` with `SimilarPattern` cases.

## Type Model For Planning

Use a minimal internal type model, not Python runtime classes:

- `PrimitiveType("string" | "int" | "float" | "bool" | "null" | "unknown")`
- `ListType(item)`
- `DictType(key, value)`
- `ProbableType(inner)`
- `NamedType("Report")`
- `MemoryType(kind, kwargs)` for `memory.episodic`, `memory.semantic`, `memory.working`
- `AgentHandleType(result_type)` if useful for `spawn`
- `UnknownType` for unresolved calls, imports, and expressions the v1 analyzer cannot infer.

Type inference can stay deliberately shallow:

- Literals infer primitive types.
- `LetStmt` with annotation uses the annotation as the expected type for initializer checks.
- `LetStmt` without annotation uses initializer type.
- `Identifier` reads from the current scope.
- `Member(expr, "value")` on `probable<T>` returns `T`, but may still be unsafe unless the expression is currently gated.
- `Call(Identifier("ask"), ...)` returns `UnknownType` unless the containing `LetStmt` annotation provides `probable<T>`.
- User function calls return the predeclared return type if known.
- Unknown calls return `UnknownType` and should not cascade noisy warnings.

## Confidence-Gate Checks

ANLY-01 requires warning when `probable<T>` is used where `T` is expected without an explicit confidence gate.

Recommended rule:

- If expected type is `T` and actual type is `probable<T>`, emit warning unless the expression is known gated in the current branch.
- A `ConfidenceGate(target=Identifier("intent"), op=">=" or ">", threshold=...)` narrows `intent` inside the `then_body`.
- For `<=` or `<`, narrow only the `else_body`.
- For `==`, narrow the `then_body` only if threshold is high enough to be meaningful. Simpler v1 rule: only `>=` and `>` produce narrowing.
- Accessing `intent.value` outside a gated branch should warn if `intent` is `probable<T>`.
- Accessing `intent.value` inside the branch guarded by `if intent @ p >= N` should not warn.
- Returning `intent` from a function declared `-> string` should warn when `intent` is `probable<string>`.
- Passing `intent` to a parameter typed `string` should warn when the callee signature is known.
- Assigning `intent` to `let x: string` should warn.

Diagnostics should use the span of the unsafe expression, not the enclosing statement. Message shape:

`file.voss:12:16: warning ANLY001: unguarded probable<string> used where string is expected`

Hint:

`Add a confidence gate such as if intent @ p >= 0.80 { ... } or pass intent.value only inside the gated branch.`

Avoid warning on:

- `let intent: probable<string> = ask(...)`.
- Returning a `probable<string>` from a function declared `-> probable<string>`.
- Passing a `probable<T>` to a parameter typed `probable<T>`.
- Storing or forwarding probable values when no concrete `T` is expected.

## Token Budget Estimation

ANLY-02 should warn when a `ctx` block likely exceeds its declared budget. This must stay approximate and deterministic.

Recommended estimator:

- Add a `TokenEstimator` protocol with `estimate_expr(expr, scope) -> int` and `estimate_stmt(stmt, scope) -> int`.
- Default estimator uses local heuristics:
  - String literal: `max(1, len(text) // 4)`.
  - Numeric/bool/null: `1`.
  - Identifier: use recorded size estimate if known; otherwise `0` to avoid false positives.
  - Binary string concatenation: sum both sides.
  - List/dict literals: sum elements plus small overhead.
  - `include expr`: estimate the expression payload.
  - `ask("literal")`: estimate prompt literal plus currently included context.
  - Unknown call result: `0` unless assigned from a literal or explicit known local estimate.
- Track estimates for `let` bindings when the initializer is statically estimable.
- In a `CtxBlock`, sum explicit `include` statements, literal `ask(...)` prompts, and statically known local values included into context.
- Emit a warning only when estimate exceeds budget by a clear margin, e.g. `estimate > budget`. Do not warn for unknown estimates.

Use `BudgetArg.unit == "tokens"` and `BudgetArg.name == "budget"` for `ctx`. If Phase 2 stores name differently, the planner should normalize through helper functions rather than spreading field checks.

Diagnostic shape:

`warning ANLY002: ctx block static token estimate 4,180 exceeds declared budget 3,000`

Hint:

`Increase the ctx budget, include less context, or add a more aggressive compression strategy.`

Important limitation to document in code comments/tests: this is not a proof. It is an early warning to catch obvious oversize literals and included known values; runtime remains authoritative.

## Compile-Time Similar Index Emission

ANLY-03 requires each `match` block's `similar(...)` cases to be embedded once at compile time and stored in `.voss-cache/<program>.idx`.

The current runtime index format supports a single matcher per file poorly if multiple match blocks exist. Recommended practical contract for Phase 3:

- Emit one JSON index file per program at `.voss-cache/<program>.idx`.
- Store a top-level manifest if multiple match blocks exist:
  - `version: 1`
  - `program: "<program stem>"`
  - `model: "sentence-transformers/all-MiniLM-L6-v2"`
  - `matches: [{match_id, threshold, cases:[...]}]`
- Each `cases` entry should use the same case shape as `SemanticMatcher.to_index()`: `{label, description, embedding}`.
- For a single match block, keep the same manifest shape rather than switching formats. Phase 4 can select by `match_id`.

This is a small extension beyond `SemanticMatcher.to_index()`, but it preserves the case schema and prevents filename collisions. If the planner wants zero schema invention, alternative is `.voss-cache/<program>-<match_id>.idx` for each `MatchStmt`; however the roadmap says `.voss-cache/<program>.idx`, so the manifest is the better fit.

Stable `match_id` options:

- `match_<line_start>_<col_start>` from `MatchStmt.span`.
- Labels: `case_<ordinal>` unless the body is a simple call where the callee name can be used safely.

Recommended emission steps:

1. Visit each `MatchStmt`.
2. Collect `SimilarPattern` cases in source order.
3. Skip match blocks with no similar cases.
4. Use `match.threshold or 0.75`.
5. Build `SemanticMatcher` with `[(description, label), ...]`; this computes embeddings once.
6. Store matcher `.to_index()["cases"]` under that match manifest entry.
7. Write `.voss-cache/<program>.idx` atomically by writing a temp file then replacing it.

Tests should inject synthetic embeddings or a fake embedder if the implementation allows it. If using `SemanticMatcher` directly, keep the real encoder test marked `live` or `slow`, because sentence-transformers model loading is not suitable for every unit test.

## Recommended Test Strategy

Add tests under `tests/analyzer/` after Phase 2 lands.

Core test files:

- `tests/analyzer/test_diagnostics.py`
  - Asserts diagnostic shape, severity, code, message, span fields, and stable string formatting.
- `tests/analyzer/test_probable.py`
  - Unsafe `let x: string = intent` where `intent: probable<string>` warns.
  - Unsafe `return intent` from `fn f() -> string` warns.
  - Unsafe `route(intent)` where `route(input: string)` warns.
  - `if intent @ p >= 0.80 { return intent.value }` does not warn.
  - `intent.value` outside the gate warns.
  - `else` branch after `>=` remains ungated and warns.
- `tests/analyzer/test_ctx_budget.py`
  - Literal prompt exceeding `ctx(budget: N tokens)` warns with `ANLY002`.
  - Known included string binding contributes to estimate.
  - Unknown call result does not warn.
  - Under-budget block is clean.
- `tests/analyzer/test_match_index.py`
  - One `match` with two `similar()` cases emits `.voss-cache/<program>.idx`.
  - Multiple match blocks in one program produce multiple manifest entries.
  - Threshold defaults to `0.75` and respects `MatchStmt.threshold`.
  - Index cases preserve source order.
- `tests/analyzer/test_examples.py`
  - Parse Phase 2 PRD examples and analyze them.
  - `classify.voss` should have no unguarded probable warning.
  - `assistant.voss` likely should warn on `response.value` unless the language decides `.value` access is always explicit enough. Research recommendation: it should warn because PRD says probable use requires a confidence gate, but this will expose a PRD example tension.

Fixture shape:

- Prefer parsing real `.voss` snippets once Phase 2 exists.
- For narrow unit tests, constructing AST nodes directly is acceptable and keeps failures localized.
- Provide a fake embedding/index writer seam so unit tests do not download models.

Verification commands for the plan:

- `pytest tests/analyzer -q`
- `pytest tests/parser tests/analyzer -q`
- `python -c "from voss import parse, analyze; ..."` smoke import once `voss/__init__.py` re-exports exist.

## Risks And Open Questions

Main risks:

- Phase 2 dependency: Phase 3 cannot be implemented cleanly until the AST names and spans from Phase 2 are real.
- PRD example conflict: `assistant.voss` uses `response.value` without a confidence gate. If ANLY-01 is interpreted strictly, this should warn. The planner should decide whether examples may contain warnings or whether `.value` access counts as explicit acknowledgement. I recommend strict warning unless gated.
- Index file schema: runtime currently reads a single matcher index, while roadmap wants one `.voss-cache/<program>.idx`. Multiple match blocks need a manifest or per-match files. Plan this explicitly before codegen.
- Embedding tests: real sentence-transformers model loads can be slow and environment-sensitive. Keep default tests hermetic.
- Type inference creep: it is easy to overbuild. V1 only needs enough type knowledge for probable warnings and obvious signature checks.
- Diagnostic churn: line/column correctness depends entirely on Phase 2 span propagation. Analyzer tests should fail loudly if spans are synthetic where source spans are expected.

## Sequencing Recommendation

1. Diagnostics and result types.
   - Verify diagnostic formatting and span propagation with direct AST fixtures.
2. Type-expression normalization and scope table.
   - Verify `TypeRef(probable<T>)` converts to `ProbableType(T)`.
3. Confidence-gate analysis.
   - Verify ANLY-01 with assignments, returns, calls, and branch narrowing.
4. Ctx token estimator.
   - Verify ANLY-02 against literal-heavy and unknown-heavy blocks.
5. Similar-case index emission.
   - Verify ANLY-03 with fake embeddings first; add one optional live/smoke test only if needed.
6. Parser integration.
   - Run analyzer over Phase 2 example fixtures.

This ordering keeps the highest-risk semantic behavior independent from the heavier embedding work.

## Validation Architecture

Nyquist-style validation is applicable because Phase 3 is not one feature; it is a compiler pass with independent correctness dimensions. Validate it across these dimensions:

- **Span fidelity:** every diagnostic points to the smallest unsafe expression or block, with real file/line/column from Phase 2 spans.
- **Type narrowing:** gated probable values narrow only in the branch where the gate logically proves confidence.
- **No-warning paths:** correct programs stay quiet, especially the PRD `classify.voss` pattern.
- **Warning paths:** each required warning has a minimal failing fixture.
- **Estimator conservatism:** obvious oversize contexts warn; unknown dynamic values do not cause noisy false positives.
- **Index determinism:** same source produces byte-stable manifest order, match IDs, labels, thresholds, and case order.
- **Index runtime compatibility:** emitted case schema can be loaded into `SemanticMatcher` or adapted by Phase 4 without recomputing compile-time case embeddings.
- **Hermetic default tests:** default `pytest` does not require network, API keys, or model downloads.
- **Integration readiness:** `AnalysisResult` carries enough data for Phase 4 codegen and Phase 5 `voss check` without re-walking the AST for diagnostics.

## Don't Hand-Roll

- Do not hand-roll embedding math or vector normalization. Reuse `SemanticMatcher` or the same sentence-transformers normalized embeddings path.
- Do not create a general-purpose type system. Build the minimal semantic model needed for `probable<T>`, function signatures, and known literals.
- Do not create a second parse-error style. Mirror `VossParseError` fields for analyzer diagnostics so CLI reporting is uniform.
- Do not make token estimates provider-specific. Static estimates should be local heuristics; runtime provider token counting remains runtime's job.

## Common Pitfalls

- Treating `.value` access as always safe. Under the PRD, confidence must be checked; `.value` alone bypasses confidence.
- Warning on unknown types. Unknown should generally suppress confidence diagnostics to avoid cascades.
- Forgetting branch locality. A gate in an `if` then-branch should not narrow after the `if` unless the analyzer can prove all paths return.
- Emitting one index per `similar()` case instead of per match/program. Runtime matching needs cases grouped by match block and preserved in source order.
- Recomputing embeddings in Phase 4. Phase 3 should write enough index metadata that codegen can reference the cache path and match ID directly.
- Using unstable labels derived from body source. Prefer ordinal labels unless a stable simple-call label is trivial.

## Planner Checklist

- [ ] Confirm Phase 2 has produced `voss/ast_nodes.py`, `voss/parser.py`, spans, and examples.
- [ ] Decide strict interpretation of `.value` on `probable<T>` outside confidence gates.
- [ ] Decide final `.voss-cache/<program>.idx` schema for multiple match blocks.
- [ ] Add analyzer diagnostics before semantic checks.
- [ ] Keep index emission injectable/fakeable for tests.
- [ ] Verify default tests do not load sentence-transformers.

---

**Research status:** Ready for Phase 3 planning once Phase 2 AST files exist.
