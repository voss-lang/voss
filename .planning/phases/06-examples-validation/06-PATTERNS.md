# Phase 06 - Pattern Map

**Phase:** Examples Validation  
**Date:** 2026-05-08  
**Owner:** GSD pattern mapper

## Boundary Assumptions

- Phase 6 proves the full pipeline for PRD section 7 examples; it does not add parser, analyzer, codegen, runtime, CLI, packaging, or Linguist features.
- Phase 6 starts only after Phase 5 is implemented and its marker is recorded. The current local tree still has Phase 5 surfaces missing or in progress, so execution must gate first.
- Default validation is deterministic CI with `StubProvider`, fake semantic indexes/embeddings, temp project roots, and no live network/model downloads.
- Optional live-provider runs are additive and `@pytest.mark.live`; they must be skipped unless credentials/config are explicit.
- Source edits are allowed only when an end-to-end example exposes a direct contract defect in the responsible surface. Keep such fixes minimal and cite the failing example/mode.

## Required Preflight Contract Gate

Create `06-01-0` as a read-only gate. It must print `phase6-examples-contract-ok` before any Phase 6 test/helper work starts.

```bash
python3 - <<'PY'
from pathlib import Path
import importlib
import tomllib

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
required_exports = [
    "parse", "to_dict", "analyze", "AnalysisResult", "Diagnostic", "EmittedIndex",
    "generate_python", "CodegenResult", "CodegenError",
]
missing_exports = [name for name in required_exports if not hasattr(voss, name)]

runtime = importlib.import_module("voss_runtime")
required_runtime = [
    "ProbableValue", "ContextScope", "BudgetScope", "BudgetExceededError",
    "SemanticMatcher", "VossAgent", "AgentHandle", "gather",
    "EpisodicMemory", "SemanticMemory", "WorkingMemory", "tool", "StubProvider",
]
missing_runtime = [name for name in required_runtime if not hasattr(runtime, name)]

required_files = [
    Path("tests/parser/examples/classify.voss"),
    Path("tests/parser/examples/support.voss"),
    Path("tests/parser/examples/research.voss"),
    Path("examples/raw_python/classify.py"),
    Path("examples/raw_python/support.py"),
    Path("examples/raw_python/research.py"),
    Path("tests/codegen/test_examples.py"),
    Path("tests/cli/test_compile.py"),
    Path("tests/cli/test_run.py"),
    Path("voss/cli.py"),
]
missing_files = [str(path) for path in required_files if not path.exists()]

pyproject = tomllib.loads(Path("pyproject.toml").read_text())
script = pyproject.get("project", {}).get("scripts", {}).get("voss")
bad_script = [] if script == "voss.cli:main" else [script]

if missing_ast or missing_exports or missing_runtime or missing_files or bad_script:
    raise SystemExit(
        "Phase 6 contract incomplete; "
        f"missing_ast={missing_ast}; missing_exports={missing_exports}; "
        f"missing_runtime={missing_runtime}; missing_files={missing_files}; "
        f"bad_script={bad_script}"
    )
print("phase6-examples-contract-ok")
PY
```

Downstream Phase 6 plans must require this marker or rerun the read-only gate. If it fails, stop and report the missing contract; do not patch around missing Phase 1-5 work.

## Likely File Map

| File | Action | Role | Pattern |
|------|--------|------|---------|
| `tests/examples/__init__.py` | create | Test package marker | Empty file only. |
| `tests/examples/helpers.py` | create | Shared example harness | Temp project roots, parser-example copying, CLI invocation, generated module execution, `StubProvider` setup, fake manifest writes, stdout normalization, cache-artifact assertions. |
| `tests/examples/test_helpers.py` | create | Harness tests | Prove helpers use temp dirs, never repo-local `.voss-cache`, and can run subprocess commands with captured stdout/stderr/exit code. |
| `tests/examples/test_classify_e2e.py` | create | EX-01 | `classify.voss` through `check`, `compile` + generated module, `python3 generated.py`, and `voss run`; compare confident and low-confidence behavior to `examples/raw_python/classify.py`. |
| `tests/examples/test_support_e2e.py` | create | EX-02 | Fake `.voss-cache/support.idx`, synthetic `SemanticMatcher._encode`, route/fallback parity with raw support example, and CLI command coverage. |
| `tests/examples/test_research_e2e.py` | create | EX-03 | Spawn/gather happy path and `within/fallback` timeout parity with raw research example under `StubProvider`. |
| `tests/examples/test_cli_matrix.py` | create | Cross-example matrix | All three examples pass `voss check`, `voss compile`, `python3 generated.py`, and `voss run` with explicit exit/stdout assertions. |
| `tests/examples/test_live_examples.py` | optional | Live-provider smoke | Mark every test `@pytest.mark.live`; skip unless configured provider/model/env exists. Record sanitized output only in execution summary. |
| `tests/parser/examples/*.voss` | read-only fixture | Canonical PRD inputs | Do not rewrite in Phase 6. Missing/invalid syntax belongs to Phase 2 unless execution proves a fixture drift bug. |
| `examples/raw_python/*.py` | read-only oracle | Semantic baseline | Reuse existing integration-test patterns. Do not edit unless Phase 1 raw oracle is directly wrong. |
| `samples/*.voss` | read-only mirror | Repo/tooling samples | Phase 6 may verify they match parser examples after Phase 5 creates them; fixes belong to Phase 5 assets. |
| `voss/cli.py` | limited bug-fix only | Command orchestration | Only fix proven `check`/`compile`/`run` contract defects: emit-index flag, temp output, subprocess exit/stdout, cache path handling. |
| `voss/codegen.py` | limited bug-fix only | Generated Python contract | Only fix generated example defects: missing runtime imports, bad async lowering, manifest consumption, stdout entrypoint, final newline/import safety. |
| `voss/analyzer.py` | limited bug-fix only | Diagnostics/indexes | Only fix direct example contract defects: unsafe `.voss-cache`, missing support manifest, incorrect probable warning. |
| `voss_runtime/*` | limited bug-fix only | Runtime behavior | Only fix direct mismatch between generated examples and raw Python runtime semantics. |

## Existing Patterns To Reuse

- Raw Python integration tests in `tests/integration/test_classify_example.py`, `test_support_example.py`, and `test_research_example.py`.
- `StubProvider` registration via `voss_runtime.providers.register("__stub__", stub)` and `configure(default_model="__stub__")`, followed by `reset_config()`.
- Parser examples in `tests/parser/examples/classify.voss`, `support.voss`, and `research.voss` as canonical Voss inputs.
- Phase 4 codegen example/snapshot patterns from `04-06-PLAN.md`: parse, analyze, generate, `ast.parse`, execute under stubs, compare raw Python.
- Phase 5 CLI patterns from `05-03-PLAN.md` and `05-06-PLAN.md`: `compile` writes after successful analysis/codegen; `run` executes `subprocess.run([sys.executable, generated_path])`.
- `.voss-cache` temp-dir safety from analyzer/codegen plans: fixtures under `tmp_path`, no repository-local `**/.voss-cache/*.idx` after default tests.
- Subprocess checks with captured `stdout`, `stderr`, and return code; do not use in-process `exec`, `eval`, `runpy`, or import execution for CLI `run` verification.

## Command Data Flow

For each example: `classify.voss`, `support.voss`, `research.voss`.

1. `voss check EXAMPLE.voss`
   - Read source -> `parse(source, file=path)` -> `analyze(..., emit_indexes=False)` -> print diagnostics -> exit `0` only when no errors.
   - Assert no generated `.py` and no `.voss-cache` artifacts.
2. `voss compile EXAMPLE.voss -o tmp/generated.py --project-root tmp --cache-dir .voss-cache`
   - Read source -> parse -> analyze with `emit_indexes=True` -> emit semantic manifest when needed -> `generate_python(..., analysis=result)` -> atomic write.
   - `support.voss` should produce/use a deterministic program manifest shaped like `{version, program, model, matches:[{match_id, threshold, cases:[{label, description, embedding}]}]}`.
3. `python3 tmp/generated.py`
   - Run in a temp cwd/environment configured for deterministic provider behavior.
   - Capture exit code/stdout/stderr. Exit must be `0`; stderr must not contain tracebacks; stdout must match the normalized expected example output.
4. `voss run EXAMPLE.voss`
   - Compile to temp generated Python -> execute with `sys.executable` subprocess -> forward/capture stdout/stderr -> return generated process exit code.
   - Assert behavior matches `voss compile` + `python3 generated.py`.

Expected per-example focus:
- `classify`: confident stub returns `cancel_subscription`; low-confidence/empty stub returns `unknown`.
- `support`: angry/refund/auth messages route to deterministic handlers; generic message falls through to `ContextScope` and returns stub text.
- `research`: happy path returns a non-empty summary; timeout path falls back to `"\n---\n".join(reports)`.

## Test And Fixture Strategy

- Keep canonical `.voss` inputs in `tests/parser/examples/`; copy into temp project dirs for CLI tests.
- Use raw Python examples as the oracle, not duplicated expected algorithms in Phase 6 tests.
- Build helper assertions for:
  - command result shape: `returncode`, `stdout`, `stderr`
  - generated Python parseability with `ast.parse`
  - no compiler imports in generated output
  - no repo-local `.voss-cache/*.idx`
  - normalized stdout comparisons
- For `support`, prefer fake semantic manifests plus synthetic encoder vectors. Do not instantiate a real sentence-transformers model in default tests.
- For subprocess runs, pass deterministic provider configuration through supported runtime environment/config seams. If none exists after Phase 5, classify that as a runtime/CLI contract defect rather than weakening tests.
- Generated output comparisons should ignore nondeterministic temp paths but should not ignore semantic output, tracebacks, exit codes, or missing stdout.
- Optional live tests must:
  - be isolated in `test_live_examples.py`
  - use `@pytest.mark.live`
  - skip without explicit provider/model config
  - assert only stable behavior: command exits `0`, stdout non-empty, no traceback, no repo-local artifacts

## Non-Goals

- No new language syntax, examples, scaffolds, CLI commands, formatter, package manager, or provider abstraction.
- No edits to `ROADMAP.md`, `STATE.md`, `REQUIREMENTS.md`, or SecondBrain.
- No broad refactors of parser, analyzer, codegen, CLI, or runtime.
- No live-provider dependency in default CI.
- No snapshot churn unless generated output behavior/readability is already under Phase 4 ownership.

## Executor Checklist

- [ ] Confirm `06-01-0` prints `phase6-examples-contract-ok`.
- [ ] Add `tests/examples` helpers before individual example tests.
- [ ] Validate `classify.voss` through `check`, `compile`, `python3 generated.py`, and `voss run`.
- [ ] Validate `support.voss` with fake semantic manifest/encoder and route/fallback parity.
- [ ] Validate `research.voss` happy path and timeout fallback parity.
- [ ] Add CLI matrix coverage across all three examples.
- [ ] Keep all generated files/cache files under temp dirs.
- [ ] Run `pytest tests/examples -q`.
- [ ] Run `pytest tests/parser tests/analyzer tests/codegen tests/cli tests/examples -q`.
- [ ] Run editable-install smoke from Phase 5 before final Phase 6 sign-off.

## PATTERN MAPPING COMPLETE

File written:
- `.planning/phases/06-examples-validation/06-PATTERNS.md`
