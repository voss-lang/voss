# Phase 04 - Pattern Map

**Phase:** Codegen
**Date:** 2026-05-07
**Owner:** GSD pattern mapper

## Boundary Assumptions

- Current source is mid-Phase 2. Phase 4 must treat the full Phase 2 AST and Phase 3 analyzer API as incoming contracts, not invent local shims.
- Add a blocking `04-01-0` preflight before implementation. It must fail fast unless required full-program AST nodes, parser examples, and Phase 3 exports exist.
- Codegen targets the real async `voss_runtime` APIs. Ignore stale sync PRD snippets that use plain `with ContextScope(...)`.
- Codegen must not execute Voss/user code, import user `use` targets, call model providers, or compute embeddings.
- Default tests must be hermetic: `StubProvider`, fake Phase 3 index manifests/builders, synthetic matcher embeddings, no live network/model downloads.

## Required Preflight Pattern

Create `04-01-0` as a read-only executable gate before any codegen module/test work:

```bash
python3 - <<'PY'
from pathlib import Path
import importlib

ast = importlib.import_module("voss.ast_nodes")
required_ast = [
    "Program", "Span", "LetStmt", "FnDecl", "AgentDecl", "AgentOptions",
    "PromptDecl", "ClassDecl", "ClassField", "UseStmt", "Decorator",
    "IfStmt", "MatchStmt", "MatchCase", "SimilarPattern", "WildcardPattern",
    "ExprPattern", "CtxBlock", "WithinFallback", "TryCatch", "ReturnStmt",
    "YieldStmt", "IncludeStmt", "BudgetArg", "ConfidenceGate", "SpawnExpr",
    "Call", "Arg", "Member", "Identifier", "TypeRef", "QualName",
]
missing_ast = [name for name in required_ast if not hasattr(ast, name)]

voss = importlib.import_module("voss")
required_exports = ["parse", "analyze", "AnalysisResult", "Diagnostic", "EmittedIndex"]
missing_exports = [name for name in required_exports if not hasattr(voss, name)]

required_files = [
    Path("tests/parser/examples/classify.voss"),
    Path("tests/parser/examples/support.voss"),
    Path("tests/parser/examples/research.voss"),
]
missing_files = [str(path) for path in required_files if not path.exists()]

if missing_ast or missing_exports or missing_files:
    raise SystemExit(
        f"Phase 4 contract incomplete; missing_ast={missing_ast}; "
        f"missing_exports={missing_exports}; missing_files={missing_files}"
    )
print("phase4-codegen-contract-ok")
PY
```

If this fails, stop Phase 4 and report the missing symbols/files. Do not add fallback AST classes or analyzer substitutes inside codegen.

## Likely File Map

| File | Action | Role | Data Flow | Closest Analogs | Executor Patterns |
|------|--------|------|-----------|-----------------|-------------------|
| `voss/codegen.py` | create | Main public emitter | `Program` + `AnalysisResult` -> readable Python source + metadata | `voss/analyzer.py` planned API, `voss/parser.py` public entry shape | Expose `generate_python(program, *, source_path=None, analysis=None, cache_dir=".voss-cache") -> CodegenResult`. If `analysis is None`, call `analyze`; if `analysis.ok` is false, refuse emission. Keep output pure: no execution, no embeddings, no provider calls. |
| `voss/codegen.py` `CodegenResult` | create | Returned compile artifact metadata | source/import decisions/async-main flag -> CLI/tests | `voss.diagnostics.AnalysisResult` frozen result pattern | Use frozen/slotted dataclass with `source: str`, `imports: tuple[str, ...]`, `requires_async_main: bool`, `analysis: AnalysisResult | None`. End source with exactly one newline. |
| `voss/codegen.py` `PythonWriter` | create | Indentation and line writer | statement emitter -> stable line list | `voss/parser.py` small helper style | Four spaces. Deterministic blank lines between top-level declarations. Keep it tiny: `write`, `blank`, indent context helper if useful. Validate with `ast.parse`. |
| `voss/codegen.py` `ImportCollector` | create | Minimal import selection | visited AST constructs -> stdlib/runtime/user imports | `voss_runtime/__init__.py` public export list | Emit only used names. Sort imported names within modules. Allow `asyncio`, `pathlib`, `typing`, `pydantic.BaseModel` only when needed. Never import `voss.parser`, `voss.analyzer`, or broad runtime names by default. |
| `voss/codegen.py` `ExpressionEmitter` | create | Inline Python expression lowering | `Expr` nodes -> Python expression strings | `voss/parser.py` expression ladder; `tests/parser/test_expressions.py` | Preserve identifiers unless Python keyword, parenthesize nested `BinOp`/`UnaryOp`, lower `spawn Agent(x)` to `Agent().spawn(x)`, lower `gather(..., timeout: 30s)` to `await gather(..., timeout=30)` only in await-capable contexts. |
| `voss/codegen.py` `StatementEmitter` | create | Statements/declarations lowering | `Stmt`/`Decl` nodes -> writer lines | `examples/raw_python/*` are semantic targets | Emit every Voss `fn` as `async def`; wrap top-level executable statements in `async def main()` and `asyncio.run(main())`. Preserve source order. |
| `voss/__init__.py` | modify | Public compiler API export | package import -> codegen API | Existing `parse` export; Phase 3 export plan | Add `generate_python` and `CodegenResult`; preserve existing `parse`, `VossParseError`, analyzer exports, and any Phase 2 serializer export. |
| `tests/codegen/__init__.py` | create | Test package marker | pytest collection | `tests/parser/__init__.py`, `tests/integration/__init__.py` | Empty file only. |
| `tests/codegen/conftest.py` | create | Fixtures and helpers | AST/parser fixtures + fake analysis/indexes -> codegen tests | `tests/parser/conftest.py`, planned `tests/analyzer/conftest.py` | Prefer parser-backed examples after contract gate. For focused units, direct AST construction is acceptable. Provide `assert_python_parses(source)` and fake `AnalysisResult` helpers. |
| `tests/codegen/test_writer.py` | create | Writer/readability foundation | writer output -> stable text/`ast.parse` | parser unit tests with direct assertions | Test indentation, blank lines, final newline, no minified block output. |
| `tests/codegen/test_imports.py` | create | Import minimality and `use` | AST `UseStmt`/construct usage -> imports | `voss_runtime/__init__.py`; Phase 2 `UseStmt` plan | Assert `use foo::bar` -> `from foo import bar`; `use foo::bar::baz` -> `from foo.bar import baz`; forbidden compiler imports absent. |
| `tests/codegen/test_expressions.py` | create | Expression lowering | expression AST -> Python snippets | `tests/parser/test_expressions.py` | Cover literals, calls, named args, members, indexes, lists, dicts, lambdas, spawn, gather timeout unit normalization. Every snippet parses or is embedded in an async wrapper when it contains `await`. |
| `tests/codegen/test_statements.py` | create | Basic statement/declaration lowering | `let`/`fn`/`return`/`if`/top-level -> Python module | `examples/raw_python/classify.py` | Assert all functions are `async def`; top-level statements live under `main`; confidence gates use explicit `.confidence`/`.value` readable lowering. |
| `tests/codegen/test_runtime_constructs.py` | create | Runtime primitive lowering | ctx/within/try/memory/probable AST -> async runtime Python | `voss_runtime/context.py`, `budget.py`, memory modules, `examples/raw_python/research.py` | Assert `async with ContextScope(...)`, `await ctx.add`, `await ctx.ask`, `try/except BudgetExceededError`, and `await run_with_budget(...)`. |
| `tests/codegen/test_semantic_match.py` | create | `match similar` + index use | Phase 3 `EmittedIndex`/fake manifest -> generated matcher code | `voss_runtime/semantic.py`, `tests/test_semantic_matcher.py`, Phase 3 `test_match_index.py` plan | Use fake `.voss-cache/<program>.idx` JSON. Codegen reads manifest metadata or generated source references it; tests must not instantiate real sentence-transformers. |
| `tests/codegen/test_agents_tools_prompts.py` | create | Agent/tool/prompt/class lowering | decl AST -> VossAgent/Pydantic/tool code | `voss_runtime/agent.py`, `tools.py`, `tests/test_agent.py`, `tests/test_tools.py` | `agent` -> `class Name(VossAgent)` with `async def run`; `@tool fn` -> `@tool` above async function; `prompt` -> constants; `class` -> `BaseModel`. |
| `tests/codegen/test_examples.py` | create | GEN-05 semantic equivalence | parse -> analyze(fake indexes) -> generate -> exec under stub -> compare raw examples | `tests/integration/test_*_example.py`, `examples/raw_python/*` | Execute generated modules in temp dirs with `StubProvider`. Monkeypatch matcher encoding or use fake manifest. Compare behavior to raw Python examples without live providers. |
| `tests/codegen/snapshots/*.py` | create if useful | Readability golden files | generated example source -> stable reviewable output | `tests/parser/golden/` planned snapshot pattern | Keep snapshots small and intentional. Parse every snapshot with `ast.parse`; no generated source line should become a minified multi-statement block. |
| `tests/codegen/helpers.py` | create only if duplication appears | Shared compile/exec assertions | source text/temp module -> execution result | Integration test fixtures | Add only after two or more tests duplicate compile/exec plumbing. Keep helpers test-local, not production code. |
| `voss_runtime/*` | avoid | Runtime target contract | generated Python imports runtime | Existing runtime implementation | Do not edit for Phase 4 unless a proven contract mismatch blocks codegen and the blocker is recorded. Prefer codegen-local manifest loading over runtime churn. |
| `voss/ast_nodes.py`, `voss/parser.py`, `voss/grammar.lark` | avoid | Input contract | parse source -> AST consumed by codegen | Phase 2 plans/source | Do not change during Phase 4 except explicit integration blocker resolution. Missing AST nodes belong to Phase 2, not codegen. |
| `voss/analyzer.py`, `voss/diagnostics.py` | read-only dependency | Analysis/index contract | analyzer result -> codegen gate + match metadata | Phase 3 plans | Codegen consumes `AnalysisResult.ok`, diagnostics, and `EmittedIndex`; it must not duplicate analyzer checks. |

## Codegen Data Flow

1. **Contract gate:** verify full AST, parser examples, and Phase 3 public analyzer exports.
2. **Analyze or validate analysis:** if no `AnalysisResult` is passed, call `analyze(program, source_path=..., cache_dir=...)`; stop on `errors`.
3. **Prepass imports/declarations:** collect generated functions, classes, agents, prompts, `use` imports, and runtime names needed by constructs.
4. **Emit declarations in source order:** prompts/constants, Pydantic classes, tool functions, agents, ordinary functions, then top-level `main` wrapper if needed.
5. **Lower runtime constructs async-first:** `ctx`, `within/fallback`, agents, `gather`, and generated function calls that are known Voss functions are awaited.
6. **Return source only:** generated code is parsed/executed by tests or later CLI; codegen itself does not run it.

## Construct Patterns

- `probable<T>`: type annotation/import `ProbableValue`; confidence gate lowers to readable confidence check and branch-local `.value` use. Analyzer owns safety warnings.
- Global `ask(...)`: decide once in Plan 04-01. Recommended lowering is an implicit `async with ContextScope(token_budget=4000) as ctx:` only when no explicit ctx is active, to keep PRD §7.1 compiling against current runtime.
- `ctx`: `async with ContextScope(token_budget=N) as ctx:`; `include x` -> `await ctx.add(x)`; `ask("...")` -> `await ctx.ask("...")`; `yield` inside ctx should become a returned value in the surrounding generated function shape.
- `within/fallback`: prefer nested async primary helper plus `await run_with_budget(_primary(), token_limit=..., latency_ms=..., cost_usd=...)`; catch `BudgetExceededError` for fallback.
- `match similar`: consume Phase 3 manifest/index metadata. Do not recompute embeddings. Load/select `match_id` and instantiate `SemanticMatcher(cases, threshold, embeddings=...)` or generated local manifest helper.
- `use`: no dynamic imports. `("foo","bar")` -> `from foo import bar`; `("foo","bar","baz")` -> `from foo.bar import baz`.
- `agent`: emit `class Name(VossAgent)` with class attrs from `AgentOptions` and `async def run(...)`. `spawn` remains sync and returns an `AgentHandle`; `gather` is awaited.
- `@tool`: emit `@tool` immediately above the generated Python function. Let runtime schema generation inspect Python signatures.
- `prompt`: emit constants such as `SUPPORT_PROMPT = "..."`; inheritance concatenates parent constant plus child text.
- `class`: emit `class Report(BaseModel): ...`; map only needed primitive/container types for v1.
- `try/catch`: direct Python `try:` / `except Exception as err:` or `except Exception:` when unnamed.
- Memory declarations: instantiate `EpisodicMemory`, `SemanticMemory`, or `WorkingMemory` from `TypeRef` kwargs; preserve constructor kwargs and unit normalization.

## Test Patterns

- Start with `pytest tests/codegen/test_writer.py tests/codegen/test_imports.py -q`, then broaden to `pytest tests/codegen -q`.
- Every emitted module/snippet should pass `ast.parse` or `compile(source, filename, "exec")`.
- Use `StubProvider` setup from `tests/integration/test_classify_example.py` and `test_research_example.py` for executable tests.
- Use `SemanticMatcher` synthetic-embedding patterns from `tests/test_semantic_matcher.py` and monkeypatch-before-import pattern from `tests/integration/test_support_example.py`.
- Keep `.voss-cache` fixtures under `tmp_path`; no repository-local generated indexes after tests.
- Forbidden in default tests: real API keys, live providers, network, sentence-transformers download, Chroma external state, and arbitrary user dependency imports.

## Non-Goals

- No parser/AST implementation work.
- No second analyzer or type checker.
- No Python formatter, LibCST/astor/Jinja/Mako dependency, or broad codegen framework.
- No live semantic/model behavior validation; Phase 6 owns live end-to-end examples.
- No speculative name normalization. Preserve Voss identifiers unless they are Python keywords.

## Executor Checklist

- [ ] Run `04-01-0` and require `phase4-codegen-contract-ok`.
- [ ] Add codegen result/writer/import collector before construct emitters.
- [ ] Make async runtime lowering the default from the first generated function.
- [ ] Wire analyzer error blocking before emitting source.
- [ ] Add fake manifest/index tests before `match similar` codegen.
- [ ] Add snapshots while output is still small enough to review.
- [ ] Verify with `pytest tests/codegen -q` and then `pytest tests/parser tests/analyzer tests/codegen -q`.
