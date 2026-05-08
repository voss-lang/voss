# Phase 05 - Pattern Map

**Phase:** CLI, Packaging & Linguist
**Date:** 2026-05-08
**Owner:** GSD pattern mapper

## Boundary Assumptions

- Current source has the Phase 2 parser surface and `tests/parser/examples/*.voss`, but Phase 3/4 source contracts are not present yet: no `voss/analyzer.py`, `voss/diagnostics.py`, or `voss/codegen.py`.
- Phase 5 must begin with a blocking read-only `05-01-0` gate that verifies parser, analyzer, codegen, and example-file contracts. If it fails, stop Phase 5; do not add CLI fallbacks.
- `voss/cli.py` is orchestration only: path validation, Click options, parse/analyze/generate calls, diagnostics display, file writes, subprocess execution, and scaffold writes.
- `check` and `ast` are read-only. `check` must call analyzer with `emit_indexes=False`; `ast` must only parse and serialize with `to_dict`.
- `run` must execute generated Python with `subprocess.run([sys.executable, generated_py, ...])`; no `exec(...)` or in-process interpretation.
- Packaging uses `[project.scripts]`. If init scaffolds use file templates, those templates must be included in package data.
- Linguist support is local preparation only. Do not claim native GitHub Voss support before upstream Linguist registration.

## Required Preflight Pattern

Create `05-01-0` before CLI implementation. It should be a read-only executable gate:

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
required_exports = [
    "parse", "to_dict", "analyze", "AnalysisResult", "Diagnostic", "EmittedIndex",
    "generate_python", "CodegenResult", "CodegenError",
]
missing_exports = [name for name in required_exports if not hasattr(voss, name)]

required_files = [
    Path("tests/parser/examples/classify.voss"),
    Path("tests/parser/examples/support.voss"),
    Path("tests/parser/examples/research.voss"),
    Path("tests/codegen/test_examples.py"),
]
missing_files = [str(path) for path in required_files if not path.exists()]

if missing_ast or missing_exports or missing_files:
    raise SystemExit(
        f"Phase 5 contract incomplete; missing_ast={missing_ast}; "
        f"missing_exports={missing_exports}; missing_files={missing_files}"
    )
print("phase5-cli-contract-ok")
PY
```

## Likely File Map

| File | Action | Role | Data Flow | Closest Analogs | Executor Patterns |
|------|--------|------|-----------|-----------------|-------------------|
| `voss/cli.py` | create | Click command group and subcommands | `.voss` path -> `parse` -> `analyze` -> `generate_python` -> file/subprocess/stdout | `voss/parser.py` public wrapper style; `voss/ast_serializer.py`; Phase 4 `generate_python` API | Expose `main()` for `[project.scripts]`. Keep helpers private and small: `_parse_file`, `_analyze`, `_print_diagnostics`, `_compile_to_path`, `_default_output_path`. Import only public `voss` APIs. |
| `voss/cli.py::ast` | create | AST debug command | source -> parser `Program` -> `to_dict` -> JSON stdout | `tests/parser/test_examples.py` golden serializer | Read-only. Use `json.dumps(to_dict(program, normalize_spans=flag), indent=2)`. Do not use `repr(program)` or write cache/generated files. |
| `voss/cli.py::check` | create | Semantic diagnostics command | source -> `parse` -> `analyze(..., emit_indexes=False)` -> diagnostics/exit code | Phase 3 `Diagnostic.__str__`; `AnalysisResult.ok` | Warnings exit `0` by default; add `--warnings-as-errors`. Assert no `.voss-cache` writes in tests. Do not parse diagnostic strings to decide status. |
| `voss/cli.py::compile` | create | Compiler pipeline command | source -> parse -> analyze with indexes -> codegen -> atomic `.py` write | Phase 4 `CodegenResult`; parser package-data tests | Analyzer errors block writes. Default output is `SOURCE.py`; `-o/--output` overrides. Write atomically to avoid partial generated files. |
| `voss/cli.py::run` | create | Compile-and-execute command | source -> temp/generated `.py` -> `subprocess.run` -> forwarded exit code | `tests/integration/test_*_example.py`; Phase 4 executable example tests | Reuse compile pipeline, then run generated Python with `sys.executable`. Forward stdout/stderr and return subprocess status. Accept args after `--` only if planned/tested. |
| `voss/cli.py::init` | create | Project scaffold command | target dir -> template files -> parse/checkable starter project | Parser examples; package-data pattern in `tests/parser/test_package_data.py` | Fail on non-empty destinations unless `--force`. Write `.gitattributes`, `.gitignore`, `pyproject.toml`, `README.md`, `hello.voss`. Keep scaffold minimal and parser-backed. |
| `voss/templates/init/*` | create if templates chosen | File-based init templates | installed package resources -> scaffold files | `voss/grammar.lark` package data via `importlib.resources` | Prefer `importlib.resources.files("voss").joinpath(...)`. If created, update package data with `templates/init/*` and test from installed/editable package context. |
| `voss/__init__.py` | modify | Public package exports | package import -> parser/analyzer/codegen API remains stable | Current exports `parse`, `VossParseError`, `to_dict`; `voss_runtime/__init__.py` export list | Preserve all Phase 2/3/4 exports. CLI does not need to be re-exported; console script targets `voss.cli:main`. |
| `pyproject.toml` | modify | Packaging entrypoint and package data | install metadata -> `voss` executable and bundled data | Existing setuptools config and `package-data = { "voss" = ["grammar.lark", "py.typed"] }` | Add `[project.scripts] voss = "voss.cli:main"`. Keep Click dependency; do not add Typer/argparse. If templates are files, add package-data coverage in the existing style. |
| `.gitattributes` | create | Repo-level Linguist override | `.voss` files -> intended Linguist classification | Scaffold `.gitattributes`; Linguist override docs | Add `*.voss linguist-language=Voss linguist-detectable=true`. Do not overpromise stats/highlighting until Voss is in upstream `languages.yml`. |
| `samples/classify.voss`, `samples/support.voss`, `samples/research.voss` | create | Representative Voss samples for repo/tooling/upstream prep | sample source -> parse/check/compile/run tests | `tests/parser/examples/*.voss`; PRD §7 examples | Prefer syncing content from parser examples or a single canonical sample source. Avoid hello-world-only samples; Linguist upstream wants representative real code. |
| `language-metadata/voss.yml` | create | Local future-Linguist metadata | repo metadata -> future upstream PR prep | Linguist `languages.yml` fields | Mark as draft/local. Include `name`, `type: programming`, `extensions: [".voss"]`, `tm_scope`, `ace_mode: python`, `color`, `group: Python`, aliases, and Python fallback metadata. Do not imply upstream acceptance. |
| `tests/cli/test_help.py` | create | Command discovery tests | Click runner -> help output | Click `CliRunner`; parser tests with focused assertions | Assert root and subcommand help exit `0` and list `compile`, `run`, `check`, `init`, `ast`. |
| `tests/cli/test_ast.py` | create | Read-only AST command tests | temp `.voss` -> CLI -> JSON | `tests/parser/test_examples.py`, `voss/ast_serializer.py` | Assert `_node: Program` and normalized spans when requested. Assert no output files/cache files are created. |
| `tests/cli/test_check.py` | create | Diagnostic display and no-side-effect tests | temp `.voss` -> analyzer diagnostics -> exit code | Phase 3 analyzer tests | Use a fixture that emits `ANLY001`. Assert file/line/col/code text, `--warnings-as-errors`, and no `.voss-cache/*.idx`. |
| `tests/cli/test_compile.py` | create | Compile pipeline tests | temp `.voss` -> generated `.py` | Phase 4 `tests/codegen/test_examples.py`; Python `ast.parse` checks | Assert parse/analyze/generate are called through public seams, errors block writes, default/output paths work, generated Python parses. Monkeypatch public APIs if needed; no fallback compiler logic. |
| `tests/cli/test_run.py` | create | Subprocess execution tests | temp `.voss` -> generated Python subprocess | `tests/integration/test_*_example.py`; `subprocess.run` | Assert stdout/stderr forwarding and generated process exit-code propagation. Test subprocess invocation shape, not in-process execution. |
| `tests/cli/test_init.py` | create | Scaffold tests | CLI target dir -> files -> parse/check | parser examples and package-data tests | Assert scaffold files, required `.gitattributes` line, non-empty-dir safety, and scaffold `.voss` parses. |
| `tests/packaging/test_entrypoint.py` | create or plan-level smoke | Installed console script/package-data smoke | editable install -> `voss --help` -> resources available | `tests/parser/test_package_data.py`; `pyproject.toml` | Prefer isolated temp venv for mutation safety if automated. At minimum verify `python3 -m voss.cli --help`, `[project.scripts]`, and package resources. |
| `tests/tooling/test_linguist_assets.py` | create | Tooling asset consistency | repo files -> parse/metadata assertions | parser examples, package-data tests | Assert `.gitattributes` exact line, `samples/*.voss` parse, metadata has `.voss`, `programming`, color, and clear draft/upstream wording. |

## Command Data Flow

1. `ast`: `Path.read_text()` -> `parse(source, file=str(path))` -> `to_dict(...)` -> stdout JSON.
2. `check`: `parse` -> `analyze(program, source_path=path, project_root=..., cache_dir=..., emit_indexes=False)` -> print diagnostics -> exit from `AnalysisResult`.
3. `compile`: `parse` -> `analyze(..., emit_indexes=True)` -> stop on errors -> `generate_python(..., analysis=result)` -> atomic write.
4. `run`: compile to temp or requested retained path -> `subprocess.run` using `sys.executable` -> return generated process exit code.
5. `init`: validate target -> copy templates or inline constants -> do not overwrite non-empty dirs without `--force`.

## Concrete Executor Patterns

- Use Click command groups; do not introduce another CLI framework.
- Keep CLI imports stable: `from voss import parse, to_dict, analyze, generate_python`; import `CodegenError` from the public export once Phase 4 provides it.
- Centralize diagnostics printing in one helper. Prefer `str(diagnostic)` from Phase 3 unless JSON output is explicitly planned later.
- Use `Path.resolve()` for `--project-root` and `--cache-dir` inputs, but leave analyzer/codegen responsible for cache path safety.
- Atomic writes: write to `output.with_name(output.name + ".tmp")`, then `replace(output)` after generation succeeds.
- For `run`, generate into `TemporaryDirectory()` unless a `--keep-generated` option is explicitly added by a plan. Preserve generated process cwd as the current project root unless tests define otherwise.
- Tests should default to `CliRunner` for help/read-only commands and `subprocess.run` for installed command/run behavior.
- Keep default tests hermetic: `StubProvider`, fake manifests, no live providers, no network, no sentence-transformers downloads.

## Linguist Reality Check

- `.gitattributes` can record the intended language with `linguist-language=Voss`, but GitHub will not treat Voss as a native known language until Voss is registered upstream in github-linguist.
- `linguist-detectable=true` only affects known languages in stats. Phrase docs/tests as "prepared for future Linguist registration," not "native GitHub support."
- Immediate GitHub-native syntax highlighting is not guaranteed until upstream registration, but metadata should still record `group: Python`, `ace_mode: python`, and a Python fallback field for future Linguist/editor use while preserving the exact Voss declaration required by TOOL-01.

## Non-Goals

- No parser, analyzer, codegen, runtime, or provider fallback implementations inside the CLI.
- No `voss fmt`, watch mode, config-file system, plugin system, package manager, or PyPI publishing in Phase 5.
- No edits to `voss_runtime/*` unless a later execution blocker proves an upstream contract mismatch and ownership is explicitly expanded.
- No source rewrites of parser examples just to satisfy CLI/tooling tests.

## Executor Checklist

- [ ] Run `05-01-0` and require `phase5-cli-contract-ok`.
- [ ] Add help/entrypoint tests before the Click shell.
- [ ] Implement read-only `ast` and `check` before write/execute commands.
- [ ] Implement `compile` before `run`; `run` must reuse compile pipeline and subprocess execution.
- [ ] Add `init` templates/package data together with package-data tests.
- [ ] Add `.gitattributes`, representative `samples/`, and draft local language metadata without claiming upstream support.
- [ ] Verify with `pytest tests/cli tests/tooling -q`, then full parser/analyzer/codegen/CLI/tooling suite, then editable-install smoke.
