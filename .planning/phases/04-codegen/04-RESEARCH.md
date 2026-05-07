# Phase 4: Codegen - Research

**Date:** 2026-05-07
**Phase:** 04-codegen
**Objective:** Identify what the planner needs to know before implementing GEN-01 through GEN-05.

## Context Summary

Phase 4 translates a validated Voss AST into readable Python that imports `voss_runtime` and behaves like the hand-written Phase 1 examples. This is not a parser or analyzer phase. Codegen should consume Phase 2 AST dataclasses plus Phase 3 `AnalysisResult`/index metadata, then emit Python source.

Important current-state facts:

- Graphify was attempted before this research and failed because `graphify-out/graph.json` does not exist.
- No Phase 4 `CONTEXT.md` exists, so this research is based on roadmap/requirements, Phase 1-3 artifacts, current source, tests, and `PRD.md`.
- Current `voss/` source is still a partial Phase 2 implementation. `voss/ast_nodes.py` currently ends at expression-level nodes (`Program`, literals, `TypeRef`, `Arg`, `Call`, `Lambda`, `SpawnExpr`, `ConfidenceGate`) and does not yet contain `LetStmt`, `FnDecl`, `AgentDecl`, `CtxBlock`, `WithinFallback`, `MatchStmt`, `TryCatch`, `UseStmt`, or related full-program constructs.
- There is no `voss/analyzer.py` or `voss/diagnostics.py` yet. Phase 3 is planned, not executed.
- Phase 4 planning must include a blocking executable gate for the final Phase 2/3 contracts before implementation starts. Do not invent local AST/analyzer shims in Phase 4.

## Current Relevant Code Structure

Existing compiler package:

- `voss/ast_nodes.py`
  - Current symbols: `Span`, `Node`, `Expr`, `Stmt`, `Decl`, `TypeExpr`, `Pattern`, `Program`, literal nodes, `Identifier`, `BudgetArg`, `QualName`, `TypeKwarg`, `TypeRef`, `Arg`, `BinOp`, `UnaryOp`, `Call`, `Member`, `Index`, `ListLit`, `DictLit`, `Param`, `Lambda`, `SpawnExpr`, `ConfidenceGate`.
  - Full Phase 4 depends on later Phase 2 nodes from the plans: `LetStmt`, `FnDecl`, `AgentDecl`, `PromptDecl`, `ClassDecl`, `ClassField`, `UseStmt`, `IfStmt`, `MatchStmt`, `MatchCase`, `SimilarPattern`, `WildcardPattern`, `ExprPattern`, `CtxBlock`, `WithinFallback`, `TryCatch`, `ReturnStmt`, `YieldStmt`, `IncludeStmt`, `Decorator`, `AgentOptions`.
- `voss/parser.py`
  - Current public entry: `parse(source: str, file: str = "<string>") -> Program`.
  - Current transformer handles literals, type expressions, expression precedence, calls, members, indexing, list/dict literals, lambdas, spawn, and confidence gates.
  - Later phases should preserve `parse` and add full program parsing.
- `voss/grammar.lark`
  - Current grammar is expression-focused. Comments note later plans will extend `top_stmt` with `let`, `if`, `fn`, `agent`, `prompt`, `class`, `use`, and decorators.
- `voss/exceptions.py`
  - `VossError` and `VossParseError`; Phase 3 plans add returned diagnostics rather than raising analyzer warnings.
- `voss/__init__.py`
  - Currently exports `parse` and `VossParseError`.
  - Phase 3 plans should add `analyze`, `AnalysisResult`, `Diagnostic`, `EmittedIndex`.
  - Phase 4 should add a stable codegen export, likely `generate_python` and `CodegenResult`.

Runtime package that generated Python must target:

- `voss_runtime/__init__.py`
  - Public imports include `ProbableValue`, `ContextScope`, `BudgetScope`, `BudgetExceededError`, `SemanticMatcher`, `VossAgent`, `AgentHandle`, `gather`, `EpisodicMemory`, `SemanticMemory`, `WorkingMemory`, `tool`, `ToolDescriptor`, provider config helpers.
- `voss_runtime/probable.py`
  - `ProbableValue(value, confidence)`, `.gate(threshold)`, `.unwrap(threshold)`, `__matmul__(threshold)`.
- `voss_runtime/context.py`
  - Async `ContextScope(token_budget, model=None, provider=None, compressor=...)`.
  - Async context manager; `await ctx.add(...)`; `await ctx.ask(prompt, return_type=...)`.
- `voss_runtime/budget.py`
  - Async `BudgetScope(token_limit=None, latency_ms=None, cost_usd=None, name="")`.
  - `run_with_budget(coro, token_limit=None, latency_ms=None, cost_usd=None, name="")`.
  - Raises `BudgetExceededError`.
- `voss_runtime/semantic.py`
  - `SemanticMatcher(cases, threshold=0.75, model=DEFAULT_LOCAL_MODEL, embeddings=None)`.
  - `to_index()`, `write_index(path)`, `from_index(path)`.
  - Runtime `from_index()` currently expects a single matcher schema `{model, threshold, cases}`. Phase 3 research recommends a program manifest for multiple match blocks, so Phase 4 must either consume that manifest directly or plan a small runtime helper if Phase 3 implements one.
- `voss_runtime/agent.py`
  - `VossAgent` with class attributes `system_prompt`, `tools`, `model`, `retries`, `return_type`.
  - Subclasses override `async def run(...)`.
  - `spawn()` returns an `AgentHandle`; `await gather(handles, timeout=...)` returns ordered results with `None` for failed/timed-out slots.
- `voss_runtime/tools.py`
  - `@tool` decorator wraps Python callables as `ToolDescriptor` and auto-generates tool schemas from Python signatures/type hints.
- `voss_runtime/memory/*`
  - `EpisodicMemory(capacity=20)`, `SemanticMemory(source=None, model=None, ...)`, `WorkingMemory()`.

Existing tests and examples to use as semantic targets:

- `examples/raw_python/classify.py`
- `examples/raw_python/support.py`
- `examples/raw_python/research.py`
- `tests/integration/test_classify_example.py`
- `tests/integration/test_support_example.py`
- `tests/integration/test_research_example.py`
- `tests/parser/*` for current AST/parser style.

Likely files Phase 4 will touch:

- `voss/codegen.py` - new main emitter module.
- `voss/__init__.py` - export public codegen API.
- `tests/codegen/__init__.py` - new test package.
- `tests/codegen/conftest.py` - AST/source fixtures and compile/run helpers.
- `tests/codegen/test_codegen_contract.py` - public API/import/readability contract tests.
- `tests/codegen/test_expressions.py` - expression emission coverage.
- `tests/codegen/test_constructs.py` - GEN-01 per-construct coverage.
- `tests/codegen/test_imports.py` - `use foo::bar` and import allowlist coverage.
- `tests/codegen/test_snapshots.py` - readable source snapshots.
- `tests/codegen/test_examples.py` - compile PRD examples and compare behavior to raw Python examples.
- `tests/codegen/snapshots/*.py` or inline expected strings - stable readability targets.

Files Phase 4 should not touch unless a contract mismatch is proven:

- `voss_runtime/*` - runtime API is the target contract, not codegen-owned.
- `voss/grammar.lark`, `voss/parser.py`, `voss/ast_nodes.py` - Phase 4 consumes parser output; parser fixes belong to Phase 2 unless the actual contract mismatch blocks integration and is explicitly recorded.
- Phase 3 analyzer internals except public imports/result data.

## Parser, AST, Analyzer, Runtime Contracts

### Parser/AST contracts

Codegen should require these completed Phase 2 contracts:

- Frozen, slotted dataclasses with immutable tuple sequence fields.
- Every node has `span: Span` for comments, diagnostics, and source-map-friendly errors.
- `Program.body` preserves top-level statement order.
- Declarations are statements: `FnDecl`, `AgentDecl`, `PromptDecl`, `ClassDecl`, `UseStmt` can appear in program order.
- Decorators are attached to nodes, not emitted as loose sibling statements.
- `@match_threshold(n)` is lifted into `MatchStmt.threshold`.
- `UseStmt.path` is a tuple/list of module parts for `use foo::bar`.
- `ConfidenceGate` exists only in `IfStmt.condition`, not general expressions.
- `BudgetArg` stores `name`, `unit`, `value`, and `raw`; codegen normalizes these to runtime kwargs.
- `SimilarPattern.text` preserves the compile-time string used by Phase 3 index emission.

### Analyzer contracts

Phase 4 should run only after Phase 3 provides:

- `voss.analyzer.analyze(program, *, source_path=None, project_root=None, cache_dir=".voss-cache", emit_indexes=True, index_builder=None) -> AnalysisResult`.
- `AnalysisResult.ok`, `.diagnostics`, `.warnings`, `.errors`, `.indexes`.
- `EmittedIndex(match_id, path, case_count, threshold, model)`.
- Analyzer emits `.voss-cache/<program>.idx` when match-similar cases exist, or returns enough index metadata for codegen to reference the file.
- `AnalysisResult.ok` is false for error-severity diagnostics such as unsafe index path writes.
- Codegen must not continue when `analysis.ok` is false.

Phase 4 planning should include a gate similar to:

```bash
python - <<'PY'
from pathlib import Path
import importlib

ast = importlib.import_module("voss.ast_nodes")
required_ast = [
    "Program", "Span", "LetStmt", "FnDecl", "AgentDecl", "PromptDecl",
    "ClassDecl", "ClassField", "UseStmt", "IfStmt", "MatchStmt",
    "MatchCase", "SimilarPattern", "WildcardPattern", "ExprPattern",
    "CtxBlock", "WithinFallback", "TryCatch", "ReturnStmt", "YieldStmt",
    "IncludeStmt", "Decorator", "BudgetArg", "ConfidenceGate", "SpawnExpr",
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

If this gate fails, Phase 4 execution should stop and report the missing symbols/files. The planner should make this task `04-01-0`.

### Runtime contracts

Generated Python should import only:

- `voss_runtime` public APIs required by emitted constructs.
- Python standard library modules required by codegen shape (`asyncio`, `pathlib`, `typing`, `pydantic` only when needed for generated model classes).
- User dependencies declared through `use` statements.

Generated Python should not import parser/analyzer/codegen internals.

The runtime is async-first. `ContextScope`, `BudgetScope`, `ctx.ask`, `ctx.add`, `VossAgent.run`, `gather`, and `run_with_budget` are async. Codegen must therefore produce async Python for AI-touching constructs. The simplest v1 recommendation is:

- Emit every Voss `fn` as `async def`.
- Emit every Voss `agent` as a `VossAgent` subclass with `async def run`.
- Wrap top-level executable statements in `async def main()` and call `asyncio.run(main())` under `if __name__ == "__main__":`.
- When calling a known generated Voss function, emit `await function(...)`.
- Runtime object methods that are known async (`ctx.add`, `ctx.ask`, `gather`, `handle.result`) must be awaited.
- Imported/user Python calls should not be auto-awaited unless Phase 3 later marks them async.

This conservative async strategy is less clever than mixed sync/async inference but reduces v1 surface area and matches the raw Python examples.

## Standard Stack

Use only the existing project stack:

- Python 3.11+.
- Dataclasses for codegen result metadata if needed.
- Plain recursive emitter/visitor. No external codegen framework.
- `ast_nodes` dataclass walking through structural `isinstance` or `match` dispatch.
- Python source emitted as strings via a small indentation writer.
- `pytest` for unit, snapshot, and semantic-equivalence tests.
- Optional `compile(source, filename, "exec")` and `ast.parse(source)` checks from the Python stdlib for syntactic validation.

Do not introduce Black, LibCST, astor, Jinja, Mako, or a custom Python AST-to-source printer for v1. A small emitter is enough because the target syntax is constrained and readability is a requirement.

## Recommended Codegen Architecture

### Public API

Recommended module: `voss/codegen.py`.

Target public API:

```python
def generate_python(
    program: Program,
    *,
    source_path: str | Path | None = None,
    analysis: AnalysisResult | None = None,
    cache_dir: str | Path = ".voss-cache",
) -> CodegenResult: ...
```

Recommended result shape:

- `CodegenResult.source: str`
- `CodegenResult.imports: tuple[str, ...]`
- `CodegenResult.requires_async_main: bool`
- `CodegenResult.analysis: AnalysisResult | None`

Keep `generate_python` pure with respect to source output. It should not execute generated code, import user modules, call providers, or compute embeddings. Analyzer/index emission is a prior step, not a hidden codegen side effect.

### Core emitter classes

Use a small writer plus a codegen visitor:

- `PythonWriter`
  - `lines: list[str]`
  - `indent_level: int`
  - `write(line: str = "")`
  - `block(header: str)` context helper if useful.
- `ImportCollector`
  - Tracks runtime names needed by generated constructs.
  - Tracks stdlib imports (`asyncio`, `typing`, `pathlib`) and user imports from `UseStmt`.
  - Emits imports deterministically.
- `NameMangler`
  - Converts Voss identifiers from camelCase to snake_case only if that convention is chosen. The raw Python examples use snake_case names, but PRD Voss examples use `classifyIntent`, `handleMessage`, `runResearch`.
  - Recommendation: preserve user spelling for v1 unless the analyzer/parser already normalizes names. Python accepts camelCase. This avoids surprising source maps and user dependency mismatches.
  - Reserve Python keywords by suffixing `_` (`class` -> `class_`) if needed.
- `ExpressionEmitter`
  - Returns inline Python expression strings.
  - Knows operator precedence enough to parenthesize nested `BinOp`/`UnaryOp`.
  - Emits calls, members, indexes, lists, dicts, lambdas, literals, spawn, gather timeout values.
- `StatementEmitter`
  - Writes Python statements with indentation.
  - Emits declarations, `if`, `match`, `ctx`, `within`, `try`, returns, yields, includes, expression statements.
- `ProgramEmitter`
  - Orchestrates import collection, declaration prepass, top-level main wrapper, emitted source assembly, and final newline.

### Import collection

Avoid hardcoding one giant runtime import. Generated files should import only names used by the source:

- `ProbableValue` when `probable<T>`, `ask(... return_type=ProbableValue)`, or explicit `ProbableValue(...)` construction appears.
- `ContextScope` for `ctx`.
- `BudgetScope`, `BudgetExceededError`, and/or `run_with_budget` for `within/fallback`.
- `SemanticMatcher` for `match similar`.
- `VossAgent`, `gather` for agents/spawn/gather.
- `EpisodicMemory`, `SemanticMemory`, `WorkingMemory` for memory declarations.
- `tool` for `@tool`.
- `BaseModel` or `pydantic.BaseModel` when `class` declarations are emitted as Pydantic models. Phase 1 context says Voss classes codegen to Pydantic subclasses.
- `asyncio` when there are top-level executable statements or generated async functions invoked from `__main__`.

Recommended import shape:

```python
import asyncio

from pydantic import BaseModel
from voss_runtime import ContextScope, ProbableValue
```

Sort imported names alphabetically within each module for stable snapshots.

### Diagnostics and analysis integration

The codegen entry should either:

1. Require an `AnalysisResult` and refuse to generate when `analysis.ok` is false, or
2. Call `analyze(...)` itself before emission.

Recommendation for Phase 4: support both, but make tests exercise explicit analysis:

- If `analysis is None`, call `analyze(program, source_path=source_path, cache_dir=cache_dir)`.
- If analysis has errors, raise/return a codegen error before emitting source.
- Warnings do not block emission.
- Codegen must use Phase 3 `EmittedIndex` metadata for `match similar`, not recompute embeddings.

### Readability rules

- Four spaces indentation.
- One top-level definition per block with one blank line between declarations.
- No minified one-line `if`/`match` blocks.
- Preserve source order of declarations and top-level statements.
- Emit short comments only where useful for generated artifacts:
  - `# Generated from <source>.voss`
  - `# Semantic index: .voss-cache/support.idx` near matcher load if applicable.
- Do not emit comments for every AST node.
- Make generated code pass `ast.parse`.

## Construct Treatment For GEN-01

| Voss construct | Recommended Python emission | Notes and dependencies |
|---|---|---|
| `probable<T>` | Type annotations map to `ProbableValue`; `ask(...)` in a probable-annotated binding emits `await ctx.ask(..., return_type=ProbableValue)` when inside `ctx`, or a helper/runtime ask only if Phase 2/3 defines top-level `ask`. | Current runtime has `ContextScope.ask`, not a global `ask`. For PRD `classify.voss`, codegen likely wraps `ask` in an implicit `ContextScope` only if the language formally allows global ask. Planner should decide this explicitly. |
| `if x @ p >= n` | `if x.confidence >= n:` or `if x @ n:`; then branch uses `x.value`. | Prefer explicit `.confidence` in generated Python for readability and to match PRD generated examples. Analyzer ensures safe use. |
| `ctx(budget: N tokens)` | `async with ContextScope(token_budget=N) as ctx:`. `include expr` -> `await ctx.add(expr)`. `yield expr` -> `return expr`. `ask("...")` -> `await ctx.ask("...")`. | Runtime is async; PRD's sync `with` examples are stale relative to implementation. |
| `within budget(tokens:, latency:, cost:) { ... } fallback { ... }` | For simple expression/return blocks, prefer `try: return await run_with_budget(_primary(), token_limit=..., latency_ms=..., cost_usd=...) except BudgetExceededError: ...`. For statement blocks, emit a nested async helper for the primary block and call `run_with_budget`. | Avoid relying on `BudgetScope.__aexit__` to redirect. Runtime raises `BudgetExceededError`; codegen catches it. |
| `match expr` with `similar(...)` cases | Use Phase 3 index metadata. Load the relevant match cases from `.voss-cache/<program>.idx`, instantiate `SemanticMatcher(..., embeddings=...)` or call a helper if added, then `match matcher.match(expr): case "case_0": ... case _: ...`. | Current `SemanticMatcher.from_index` cannot directly load Phase 3's proposed program manifest. Planner must either require Phase 3 to emit per-match files or add codegen-local manifest loading. Prefer codegen-local manifest loading to avoid runtime churn. |
| Structural `match` cases | Python `match expr: case literal:` or `if/elif` if expression patterns do not map cleanly. | V1 examples only require `similar` and wildcard. Keep structural support minimal but present if AST supports `ExprPattern`. |
| `agent Name(args) -> T` | `class Name(VossAgent): ... async def run(self, args...) -> T: ...` with class attrs for `system_prompt`, `tools`, `model`, `retries`, `return_type`. | Return Pydantic class types directly when known. |
| `spawn Agent(args)` | `Agent().spawn(args)` for an agent class. | Do not `await` spawn; it creates a task. |
| `gather(handles, timeout: 30s)` | `await gather(handles, timeout=30)`; `60s` -> `60`, `500ms` -> `0.5` if accepted for timeout seconds. | Runtime gather timeout unit is seconds. |
| Memory declarations | `history = EpisodicMemory(capacity=20)`, `knowledge = SemanticMemory(source="./docs/", model="...")`, `notes = WorkingMemory()`. | Type kwargs map to constructor kwargs. `20 turns` -> `capacity=20`. |
| `@tool fn ...` | Emit `@tool` immediately above the generated Python function. | Runtime `tool` reads Python signature/type hints/docstring. Function body still needs valid Python. |
| `prompt Base { "..." }` | Emit module constants for each prompt, e.g. `BASE_PROMPT = "..."`; derived prompt concatenates parent prompt plus child prompt. | Agent `system:` option may refer to prompt name and should map to the constant. |
| `prompt Child extends Base` | `CHILD_PROMPT = BASE_PROMPT + "\n" + "..."`. | Keep simple and readable. |
| `class Report { content: string }` | `class Report(BaseModel): content: str`. | Required by Phase 1 D-11 for structured agent outputs. Map Voss primitives to Python typing. |
| `try { ... } catch err { ... }` | Python `try:` / `except Exception as err:`. If no name, `except Exception:`. | GEN-03 requires this explicitly. Planner can later narrow exception types if syntax supports them. |
| `use foo::bar` | Python `from foo import bar` by default. `use foo::bar::baz` -> `from foo.bar import baz`. | GEN-04. Codegen should preserve only declared user dependencies. No dynamic imports. |
| ordinary `fn` | `async def name(params) -> type:`. | All Voss functions async in v1 is the simplest consistent lowering. |
| `let` | `name = expr` or `name: type = expr`; declarations without initializer for memory types instantiate memory, otherwise maybe `name: type` only if Python permits. | For local variables, prefer readable type annotations only when they add value or are needed for Pydantic/Probable semantics. |
| `return` | `return expr`; await known generated async calls inside expression only when needed. | Avoid emitting `return await` around plain runtime sync functions. |
| top-level executable statements | Wrap in `async def main(): ...` plus `if __name__ == "__main__": asyncio.run(main())`. | Keeps generated modules importable without side effects beyond declarations. |

## Open Language Decisions To Resolve During Planning

1. Global `ask(...)` semantics.
   - PRD examples call `ask(...)` outside an explicit `ctx` in `classify.voss`, but runtime only exposes `ContextScope.ask`.
   - Planning should choose one:
     - Require parser/examples to wrap `ask` in `ctx`, or
     - Generate an implicit default `ContextScope` for function bodies that call `ask` without an active `ctx`, or
     - Add a runtime global ask helper in an earlier phase.
   - Recommendation: for v1, generate an implicit `async with ContextScope(token_budget=4000) as ctx:` around direct `ask` calls only when no explicit `ctx` is active, and make the default budget a named codegen constant. This keeps PRD section 7.1 compiling.
2. Phase 3 index schema.
   - Phase 3 research recommends one `.voss-cache/<program>.idx` manifest with multiple matches.
   - Current runtime `SemanticMatcher.from_index()` expects a single matcher file.
   - Recommendation: codegen reads the manifest JSON and instantiates `SemanticMatcher(cases, threshold, embeddings=...)` for each match block. No runtime change required.
3. Async lowering.
   - Recommendation: all generated Voss `fn` become `async def` for v1. This avoids mixed async inference and matches `ContextScope`/agent runtime.
4. Name normalization.
   - Recommendation: preserve Voss identifiers in generated Python unless they are Python keywords. Do not silently convert camelCase to snake_case in v1.

## Test Strategy

Add `tests/codegen/` after Phase 2/3 contracts exist.

### Unit tests

- `tests/codegen/test_writer.py`
  - Indentation writer produces stable four-space indentation.
  - Blank lines between top-level declarations are deterministic.
- `tests/codegen/test_expressions.py`
  - Literals, identifiers, binary precedence, calls, named args, members, indexes, lists, dicts, lambdas, spawn.
  - `gather(handles, timeout: 30s)` emits `await gather(handles, timeout=30)`.
- `tests/codegen/test_imports.py`
  - Runtime imports are minimal and deterministic.
  - `use foo::bar` emits `from foo import bar`.
  - `use foo::bar::baz` emits `from foo.bar import baz`.
  - Generated files do not import `voss.parser`, `voss.analyzer`, or broad undeclared modules.
- `tests/codegen/test_constructs.py`
  - One focused fixture per GEN-01 construct.
  - `try/catch` string contains valid Python `try:` and `except`.
  - `@tool` is preserved directly above the Python function.
  - memory declarations instantiate the correct runtime classes.
  - prompt inheritance produces parent+child prompt constants.
  - class declarations produce Pydantic models.
- `tests/codegen/test_snapshots.py`
  - Golden generated Python for `classify.voss`, `support.voss`, and `research.voss`.
  - Snapshots assert readability: imports at top, one blank line between definitions, no minified blocks, no generated source lines above a reasonable length except strings.

### Integration and semantic equivalence tests

- `tests/codegen/test_examples.py`
  - Parse `tests/parser/examples/classify.voss`, analyze, generate Python, `ast.parse` it, execute it in a temp module with `StubProvider`, and compare result to `examples/raw_python/classify.py`.
  - Repeat for support and research examples.
  - Use monkeypatching patterns from `tests/integration/test_support_example.py` to avoid sentence-transformers model downloads.
  - Use fake Phase 3 index builder or prebuilt `.idx` fixture for `match similar`.

Suggested fixture shapes:

- `tests/parser/examples/*.voss` should be the source of truth once Phase 2 lands.
- `tests/codegen/fixtures/*.voss` can hold one-construct snippets if parser examples are too broad.
- `tests/codegen/snapshots/*.py` should contain expected generated source.
- `tests/codegen/helpers.py` can provide:
  - `compile_source_to_python(source: str, filename: str, tmp_path: Path) -> Path`
  - `exec_generated(path: Path, globals_overrides: dict | None = None) -> Any`
  - `assert_no_forbidden_imports(source: str)`

Verification commands for Phase 4 plans:

```bash
pytest tests/codegen -q
pytest tests/parser tests/analyzer tests/codegen -q
python - <<'PY'
from pathlib import Path
import ast
for path in Path("tests/codegen/snapshots").glob("*.py"):
    ast.parse(path.read_text(), filename=str(path))
print("codegen-snapshots-parse-ok")
PY
```

Full semantic-equivalence verification should run the generated examples with deterministic `StubProvider`, not live model providers.

## Risks, Sequencing, Blockers

### Blockers

- Phase 2 full AST/parser contract is not implemented in current source.
- Phase 3 analyzer/results/index metadata are not implemented in current source.
- Phase 4 cannot safely start until the `phase4-codegen-contract-ok` preflight passes.

### Sequencing recommendation

1. Codegen contract gate and public result shape.
   - Verify Phase 2/3 symbols, parser examples, and analyzer exports exist.
2. Writer, import collector, and expression emitter.
   - Verify generated expression snippets parse as Python.
3. Statement/declaration emitter foundation.
   - `fn`, `let`, `return`, `if`, top-level `main`, Pydantic `class`.
4. Runtime primitive emitters.
   - `probable`, `ctx`, `within/fallback`, `try/catch`, memory declarations.
5. Semantic routing and imports.
   - `match similar` through Phase 3 index manifest; `use foo::bar`.
6. Agent/tool/prompt lowering.
   - `agent`, `spawn`, `gather`, `@tool`, prompt inheritance.
7. Example integration and snapshots.
   - Compile all PRD section 7 examples, compare behavior to `examples/raw_python`.

### Main risks

- Async mismatch: PRD generated snippets show sync context managers, but runtime implementation is async. Codegen must target the real runtime, not stale PRD snippets.
- Global `ask` ambiguity: PRD examples use `ask` without `ctx`; runtime has only `ContextScope.ask`. Plan this explicitly.
- Similar-index schema mismatch: Phase 3 program manifest vs `SemanticMatcher.from_index()` single matcher loader.
- Overbroad imports: GEN-01 success criteria require only `voss_runtime` plus declared dependencies.
- Readability regression: easy to pass semantic tests while emitting hard-to-debug Python. Snapshot tests must be first-class.
- Type mapping creep: emitting perfect Python typing for all Voss types is not needed for v1. Map only what runtime/Pydantic/tool schemas need.
- Analyzer warning handling: warnings should not block codegen, but error diagnostics must block emission.
- User dependency execution: tests should not import arbitrary `use` targets unless fixtures provide local stub modules.

## Validation Architecture

Nyquist-style validation is applicable because Phase 4 is a many-surface compiler output phase. Validate at multiple dimensions rather than relying only on end-to-end examples.

Validation dimensions:

- **Contract readiness:** executable gate proves Phase 2 AST nodes, Phase 3 analyzer exports, and parser example files exist before codegen implementation.
- **Python syntax:** every emitted source string passes `ast.parse` and `compile`.
- **Import minimality:** generated Python imports only required `voss_runtime` names, standard library modules, Pydantic when needed, and declared `use` dependencies.
- **Construct coverage:** one focused fixture for every GEN-01 construct.
- **Runtime behavior:** generated examples execute with `StubProvider` and match raw Phase 1 examples.
- **Async correctness:** generated code awaits `ctx.add`, `ctx.ask`, `gather`, agent results, and generated Voss function calls where required.
- **Readability:** snapshot tests assert stable indentation, blank lines, declaration order, and non-minified blocks.
- **Analyzer integration:** codegen refuses error-severity `AnalysisResult` but emits with warnings.
- **Index compatibility:** `match similar` uses Phase 3 indexes without recomputing embeddings in Phase 4.
- **Path hygiene:** generated references to `.voss-cache` are relative/project-local and do not write files during codegen.
- **Hermetic default tests:** no network, API keys, sentence-transformers downloads, Chroma external state, or live provider calls.

## Don't Hand-Roll

- Do not hand-roll embeddings or vector matching in codegen. Use Phase 3 emitted indexes and `SemanticMatcher`.
- Do not create a second analyzer. Codegen should not re-check probable safety or token budgets.
- Do not build a general Python formatter. Emit simple readable source directly.
- Do not execute user code to discover imports, signatures, or async behavior.
- Do not add a second runtime abstraction layer inside generated code unless a tiny helper is needed for manifest loading.

## Common Pitfalls

- Emitting sync `with ContextScope(...)` against an async runtime.
- Forgetting `await` on `ctx.ask` or `gather`.
- Recomputing `similar()` embeddings in generated Python instead of using `.voss-cache`.
- Treating `use foo::bar` as `import foo::bar` instead of valid Python import syntax.
- Emitting `except Exception as None` when catch has no name.
- Turning every generated helper into a clever abstraction. Readable direct Python is the requirement.
- Letting codegen proceed after analyzer error diagnostics.
- Adding imports for all runtime names regardless of source usage.
- Losing source order of top-level declarations and executable statements.

## Planner Checklist

- [ ] Add `04-01-0` contract preflight and make all Phase 4 plans depend on it.
- [ ] Decide global `ask` lowering before implementing example codegen.
- [ ] Confirm Phase 3 index manifest shape and how codegen loads a single match block.
- [ ] Implement writer/import collector before construct emitters.
- [ ] Keep generated source snapshots in tests from the first construct wave.
- [ ] Verify generated Python with `ast.parse` in every codegen test.
- [ ] Compare compiled PRD examples against `examples/raw_python/*` under `StubProvider`.

---

**Research status:** Ready for Phase 4 planning after Phase 2 and Phase 3 execution produce their planned public contracts.
