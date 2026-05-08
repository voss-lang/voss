# Phase 5: CLI, Packaging & Linguist - Research

**Date:** 2026-05-08
**Phase:** 05-cli-packaging-linguist
**Objective:** Identify what the planner needs to know before implementing CLI-01 through CLI-06 and TOOL-01 through TOOL-03.

## Context Summary

Phase 5 should make the completed compiler usable from a shell and make `.voss` files behave well in Git/GitHub from day one. It should not implement parser, analyzer, codegen, or runtime behavior. The CLI is an orchestration layer over the Phase 2 parser, Phase 3 analyzer, Phase 4 codegen, and Phase 1 runtime.

Important current-state facts:

- Graphify was attempted before this research and failed because `graphify-out/graph.json` does not exist.
- No Phase 5 `CONTEXT.md` exists, so this research uses roadmap/requirements, prior phase artifacts, current source/tests, and external packaging/Linguist docs.
- Current source already contains a richer Phase 2 parser package than some planning docs assume: `voss/ast_nodes.py`, `voss/grammar.lark`, `voss/parser.py`, and `voss/ast_serializer.py` exist.
- Phase 3 and Phase 4 are still not implemented in source: there is no `voss/analyzer.py`, `voss/diagnostics.py`, `voss/codegen.py`, `tests/analyzer/`, or `tests/codegen/`.
- There are no `.voss` source fixtures in the repo today: `find . -name '*.voss'` returned none. Phase 5 needs samples and init scaffolds, but should not backfill parser test examples unless Phase 2/4 plans already require them.
- There is no current `voss/cli.py`, no `[project.scripts]` entry, no top-level `.gitattributes`, no `samples/`, and no Linguist metadata file.
- The repo is collaborative and the worktree can change during planning/execution. Phase 5 must not revert unrelated edits; at validation time, an unrelated untracked `.vscode/` directory existed.

## Current Relevant Code And Package Structure

Existing compiler package:

- `voss/__init__.py`
  - Current exports: `parse`, `VossParseError`, `to_dict`.
  - Phase 3 plans add `analyze`, `AnalysisResult`, `Diagnostic`, `EmittedIndex`.
  - Phase 4 plans add `generate_python`, `CodegenResult`, `CodegenError`.
  - Phase 5 should preserve all exports and add CLI importability through a new module, not by putting CLI code in `__init__.py`.
- `voss/parser.py`
  - Public entry: `parse(source: str, file: str = "<string>") -> Program`.
  - Wraps Lark errors as `VossParseError`.
  - Uses `grammar.lark` as package data. Packaging tests must keep that file installed.
- `voss/ast_serializer.py`
  - Public helper: `to_dict(node, *, normalize_spans=False)`.
  - Recommended backing for `voss ast` output. Do not create a second AST serialization format for the CLI.
- `voss/ast_nodes.py`
  - Frozen/slotted dataclasses and spans. Current nodes include `Program`, `LetStmt`, `FnDecl`, `AgentDecl`, `PromptDecl`, `ClassDecl`, `UseStmt`, `IfStmt`, `MatchStmt`, `CtxBlock`, `WithinFallback`, `TryCatch`, `ReturnStmt`, `YieldStmt`, `IncludeStmt`, `Decorator`, `BudgetArg`, and expression/type/pattern nodes.
- `voss/exceptions.py`
  - `VossError` and `VossParseError`. CLI error handling should format these cleanly and exit non-zero.
- Missing expected Phase 3/4 modules:
  - `voss/diagnostics.py`
  - `voss/analyzer.py`
  - `voss/codegen.py`

Existing runtime package:

- `voss_runtime/__init__.py`
  - Public runtime import surface includes `ProbableValue`, `ContextScope`, `BudgetScope`, `BudgetExceededError`, `SemanticMatcher`, `VossAgent`, `AgentHandle`, `gather`, `EpisodicMemory`, `SemanticMemory`, `WorkingMemory`, `tool`, `ToolDescriptor`, provider config helpers, and `StubProvider`.
- `voss_runtime/semantic.py`
  - `SemanticMatcher.from_index(path)` currently reads a single matcher schema, while Phase 3/4 plans recommend a program-level `.voss-cache/<program>.idx` manifest for multiple match blocks. CLI should not interpret semantic indexes directly; it should pass through analyzer/codegen options.

Existing tests/examples:

- `tests/parser/` covers current parser behavior but does not contain `tests/parser/examples/*.voss`.
- `tests/integration/test_*_example.py` exercise raw Python examples against `StubProvider`.
- `examples/raw_python/classify.py`, `support.py`, and `research.py` are semantic targets for codegen, not CLI scaffolds.
- Missing likely Phase 5 test dirs: `tests/cli/`, `tests/packaging/`, and `tests/tooling/` or equivalent.

Existing `pyproject.toml`:

- Build backend: setuptools.
- Package list: `["voss_runtime", "voss"]`.
- Package data: `{ "voss" = ["grammar.lark", "py.typed"] }`.
- Dependencies already include `click>=8.1.0` and `rich>=13.0.0`, so Phase 5 should use Click rather than add Typer/argparse.
- Missing `[project.scripts]` entry for `voss`.
- Coverage currently only tracks `voss_runtime`; planner may decide whether Phase 5 should broaden coverage to `voss` after compiler implementation.

## Parser, Analyzer, Codegen, Runtime Contracts

Phase 5 must consume these contracts:

- Parser:
  - `parse(source, file=...) -> Program`.
  - `VossParseError` includes file, line, column, expected tokens, got token/char, optional hint, and source excerpt.
  - `to_dict(program, normalize_spans=...)` provides a deterministic AST representation for `voss ast`.
- Analyzer:
  - Expected Phase 3 public API: `analyze(program, *, source_path=None, project_root=None, cache_dir=".voss-cache", emit_indexes=True, index_builder=None) -> AnalysisResult`.
  - `AnalysisResult` should expose `.diagnostics`, `.warnings`, `.errors`, `.ok`, and `.indexes`.
  - Diagnostics are returned data, not ordinary raised exceptions. CLI `check` and `compile` should print them in stable file/line/col format.
  - `voss check` should call analyzer with `emit_indexes=False` unless the project intentionally wants linting to create `.voss-cache` artifacts. Recommendation: no cache writes for `check`.
- Codegen:
  - Expected Phase 4 public API: `generate_python(program, *, source_path=None, analysis=None, project_root=None, cache_dir=".voss-cache") -> CodegenResult`.
  - `CodegenResult.source` is the emitted Python source. Codegen must not execute generated code.
  - `CodegenError` should represent semantic/codegen refusal, unsafe index paths, or invalid generated source.
  - `compile` and `run` should not recompute embeddings or duplicate analyzer logic; they should pass `AnalysisResult` into `generate_python`.
- Runtime:
  - Generated Python targets async `voss_runtime`; `voss run` should execute the generated program as a Python process/module rather than trying to interpret Voss in-process.
  - Default tests must remain hermetic: use `StubProvider`, fake manifests, and no live providers/model downloads.

### Required Phase 5 Contract Gate

Plan Phase 5 with a first read-only executable gate, `05-01-0`, before any CLI implementation. It should fail fast if Phase 2/3/4 contracts are incomplete.

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

If this gate fails, Phase 5 execution should stop and report missing pieces. Do not implement temporary analyzer/codegen fallbacks inside the CLI.

## Standard Stack

Use the stack already in the project:

- Click for command groups and subcommands. The PRD already selected Click and `pyproject.toml` already depends on it.
- Rich only for readable terminal output if it materially improves diagnostic display; otherwise plain Click output is enough.
- PyPA `[project.scripts]` in `pyproject.toml` for the installed `voss` executable. PyPA specifies that `[project.scripts]` maps command names to object references for console scripts.
- Setuptools package-data config for files bundled inside the Python package, such as scaffold templates if they live under `voss/templates/`.
- `subprocess.run` for `voss run` generated Python execution and for CLI integration tests.
- `pytest`, `tmp_path`, and isolated virtual environments or `python3 -m pip install -e .` checks for packaging validation.

External reference points verified on 2026-05-08:

- PyPA `pyproject.toml` spec: `[project.scripts]` corresponds to console scripts and values are object references. Source: https://packaging.python.org/en/latest/specifications/pyproject-toml/
- Setuptools package-data docs: `[tool.setuptools.package-data]` includes non-Python package files. Source: https://setuptools.pypa.io/en/latest/userguide/datafiles.html
- Click command groups are the normal abstraction for nested CLI commands. Source: https://click.palletsprojects.com/en/stable/commands-and-groups/
- Linguist overrides use `.gitattributes`; `linguist-language` controls classification/highlighting and `linguist-detectable` only includes known languages in stats. Source: https://github.com/github-linguist/linguist/blob/main/docs/overrides.md
- Linguist `languages.yml` metadata includes required fields such as `type`, `ace_mode`, `extensions`, `language_id`, and `tm_scope`, with optional `color` and `group`. Source: https://github.com/github-linguist/linguist/blob/main/lib/linguist/languages.yml
- Linguist contribution rules require representative samples and enough in-the-wild usage; hello-world tutorial samples are not accepted upstream. Source: https://github.com/github-linguist/linguist/blob/main/CONTRIBUTING.md

## Recommended CLI Architecture

Create `voss/cli.py` with a small Click group:

- `main()` as the console-script target.
- `@click.group()` root with `--version`.
- Subcommands: `compile`, `run`, `check`, `init`, `ast`.
- Small private helpers:
  - `_read_source(path: Path) -> str`
  - `_parse_file(path: Path) -> Program`
  - `_analyze_file(program, path, *, project_root, cache_dir, emit_indexes) -> AnalysisResult`
  - `_print_diagnostics(result_or_diagnostics) -> None`
  - `_default_output_path(input_path) -> Path`
  - `_write_text_atomic(path, text) -> None` if compile writes generated Python.
  - `_exit_for_diagnostics(result, *, warnings_fail=False) -> None`

Keep the CLI thin. The only logic it owns is file IO, option parsing, subprocess execution, diagnostic display, scaffold writing, and exit codes.

Recommended exit code policy:

- `0`: command completed successfully. `check` may return `0` with warnings unless planner decides warnings should fail CI.
- `1`: parse/analyzer/codegen errors or generated Python process exits non-zero.
- `2`: Click usage errors are handled by Click.

Recommended common options:

- `--cache-dir PATH` default `.voss-cache`.
- `--project-root PATH` default current working directory.
- `--verbose` for showing intermediate paths and subprocess command.
- Avoid global config files in Phase 5 unless already implemented by earlier phases.

## Command Behavior

### `voss compile SOURCE.voss`

Requirement: CLI-01.

Recommended behavior:

1. Validate source path exists and suffix is `.voss` with a clear error if not.
2. Parse source with `parse(source, file=str(path))`.
3. Analyze with `emit_indexes=True` so `match similar(...)` indexes are available for codegen/runtime.
4. Print diagnostics. Warnings do not block compilation; errors do.
5. Generate Python with `generate_python(program, source_path=path, analysis=analysis, project_root=..., cache_dir=...)`.
6. Write output to `--output` if provided, otherwise `SOURCE.py` beside the input.
7. Exit non-zero if parser/analyzer/codegen errors occur.

Options:

- `--output PATH`, `-o PATH`
- `--check/--no-check` is unnecessary if compile always analyzes. Keep it simple.
- `--cache-dir PATH`
- `--project-root PATH`
- `--verbose`

Planning note: use atomic writes to avoid leaving truncated `.py` files if generation fails mid-write.

### `voss run SOURCE.voss`

Requirement: CLI-02.

Recommended behavior:

1. Reuse compile pipeline into a temporary directory or `--output` path.
2. Execute generated Python with the current Python interpreter: `sys.executable generated.py`.
3. Forward stdout/stderr and return the generated process exit code.
4. Pass user arguments after `--` if needed. Example: `voss run app.voss -- arg1 arg2`.

Options:

- `--keep-generated PATH` to retain the generated Python for debugging. Do not add this unless tests need it; `compile` already gives users a stable artifact.
- `--cache-dir`, `--project-root`, `--verbose`.

Do not execute generated code in-process with `exec(...)`. A subprocess isolates `sys.argv`, import side effects, and working directory behavior, and it matches how users will run compiled Python.

### `voss check SOURCE.voss`

Requirement: CLI-03.

Recommended behavior:

1. Parse source.
2. Analyze with `emit_indexes=False`.
3. Print diagnostics with file path and line/column. ANLY001 unguarded probable warnings must be visible.
4. Return `0` if there are warnings only and no errors. Add `--warnings-as-errors` if CI wants strictness.

Options:

- `--warnings-as-errors`
- `--cache-dir`, but do not write indexes by default.
- `--format text|json` only if there is a concrete consumer. Default text is enough for v1.

Diagnostic output should reuse `Diagnostic.__str__` or equivalent from Phase 3. Do not format each diagnostic independently in the CLI if diagnostics already have a stable string form.

### `voss ast SOURCE.voss`

Requirement: CLI-05.

Recommended behavior:

1. Parse source.
2. Print `json.dumps(to_dict(program, normalize_spans=...), indent=2)`.
3. Default to real spans because this is a debugging command. Add `--normalize-spans` for stable snapshots/tests.

Options:

- `--normalize-spans`
- `--compact`

Do not use `repr(program)` as the primary output. The serializer exists and is deterministic.

### `voss init my-project`

Requirements: CLI-04 and TOOL-02.

Recommended behavior:

1. Create target directory unless it exists and is empty. If it exists and is not empty, fail unless `--force`.
2. Write:
   - `pyproject.toml`
   - `.gitignore`
   - `.gitattributes`
   - `src/main.voss` or `hello.voss`
   - `README.md`
3. Keep scaffold minimal and actually compilable once Phase 4 is complete.
4. `.gitattributes` must include the Voss override line. Use one line first:
   - `*.voss linguist-language=Voss linguist-detectable=true`

Recommended scaffold shape:

```text
my-project/
  .gitattributes
  .gitignore
  pyproject.toml
  README.md
  hello.voss
```

Keep templates under `voss/templates/init/` if using package data, or inline constants if there are only 4-5 short files. Because `init` scaffolds multiple files and package-data testing is required anyway, templates are cleaner.

Caveat: Linguist docs state languages not listed in `languages.yml` will not be included in language stats even with `linguist-language=Voss linguist-detectable`. The override still documents intent and should help once Voss is registered. Recommendation: emit the required Voss override, record Python parent/fallback metadata in `language-metadata/voss.yml`, and document that GitHub stats/highlighting may not treat Voss natively until upstream Linguist registration.

## Packaging Details

Implement CLI packaging through `pyproject.toml`:

```toml
[project.scripts]
voss = "voss.cli:main"
```

Package-data choices:

- Keep current `voss` package data: `grammar.lark`, `py.typed`.
- If scaffold templates are files, add them under package data:

```toml
[tool.setuptools]
packages = ["voss_runtime", "voss"]
package-data = { "voss" = ["grammar.lark", "py.typed", "templates/init/*"] }
```

Alternative setuptools syntax:

```toml
[tool.setuptools.package-data]
voss = ["grammar.lark", "py.typed", "templates/init/*"]
```

Pick one style and keep it consistent with the existing file. Do not add `MANIFEST.in` unless sdist tests prove package data is missing from source archives.

Packaging verification should cover:

- `python3 -m pip install -e .` exposes `voss`.
- `python3 -m pip install -e ".[dev]"` keeps tests working.
- `python3 -m voss.cli --help` works if `cli.py` has a module entrypoint. This is optional but useful for debugging editable installs.
- `voss --help`, `voss compile --help`, `voss run --help`, `voss check --help`, `voss init --help`, and `voss ast --help` all exit `0`.
- Installed package can still read `voss/grammar.lark` through `importlib.resources` or the current parser path.

## Linguist, `.gitattributes`, Samples, And Metadata

Requirements: TOOL-01, TOOL-02, TOOL-03.

Top-level repo changes Phase 5 should plan:

- `.gitattributes`
  - Add `*.voss linguist-language=Voss linguist-detectable=true`.
  - Do not mark generated Python as Voss. If generated code snapshots are committed, consider `tests/codegen/snapshots/*.py linguist-generated` only if stats get noisy, but that is not required by Phase 5.
- `samples/`
  - Add representative Voss programs:
    - `samples/classify.voss`
    - `samples/support.voss`
    - `samples/research.voss`
  - These can mirror PRD §7 examples but should be representative, not trivial hello-world only. Linguist upstream explicitly rejects hello-world/tutorial-only samples.
  - These should parse and, after Phase 4, compile/run through the CLI tests.
- Language metadata file in this repo for future upstream PR, e.g. `linguist/voss.yml` or `language-metadata/voss.yml`.
  - Keep it local/project-owned; do not pretend it is accepted upstream.
  - Include:
    - `name: Voss`
    - `type: programming`
    - `extensions: [".voss"]`
    - `tm_scope: "source.voss"` if a grammar exists, otherwise `tm_scope: "none"` for the draft.
    - `ace_mode: "python"` as the nearest editor fallback until a Voss-specific editor grammar exists.
    - `color: "#4B8BBE"` or another deliberate non-conflicting color.
    - `group: Python` and `fallback_highlighting: Python` as parent/fallback metadata for the future Linguist PR.
    - `aliases: ["voss"]`.

Important Linguist reality check:

- `.gitattributes linguist-language=Voss` only classifies as a language known in Linguist `languages.yml`. The upstream docs say unknown languages will not be included in stats even if `linguist-detectable` is set.
- Native GitHub syntax highlighting for Voss will require a future grammar and Linguist PR. Phase 5 can prepare metadata and samples, but it cannot guarantee native Voss highlighting on GitHub before upstream registration.
- A separate `.gitattributes` line using `linguist-language=Python` would conflict with TOOL-01's exact Voss declaration. Recommendation: satisfy TOOL-01 exactly and include Python parent/fallback metadata plus samples for the future PR.

## Recommended Test Strategy

Add focused tests around CLI behavior, packaging, and tooling. Keep them hermetic and use subprocesses for the real installed command path.

Likely test files:

- `tests/cli/test_help.py`
  - Use Click's `CliRunner` for quick help tests.
  - Assert root help lists `compile`, `run`, `check`, `init`, `ast`.
  - Assert each subcommand help exits `0` and contains command-specific options.
- `tests/cli/test_ast.py`
  - Write a small `.voss` file under `tmp_path`.
  - Invoke `voss ast --normalize-spans file.voss`.
  - Assert JSON contains `_node: Program` and expected statement nodes.
- `tests/cli/test_check.py`
  - Use a fixture that triggers `ANLY001` after Phase 3 is implemented.
  - Assert output includes file path, line/column, `warning`, and `ANLY001`.
  - Assert `--warnings-as-errors` exits non-zero.
  - Assert no `.voss-cache/*.idx` files are created by `check`.
- `tests/cli/test_compile.py`
  - Compile a simple parser/codegen-backed `.voss` fixture.
  - Assert output path defaults to `source.py`.
  - Assert generated file parses with Python `ast.parse`.
  - Assert analyzer errors block writes.
- `tests/cli/test_run.py`
  - Run a small `.voss` fixture through `voss run`.
  - Use `StubProvider` configuration or a no-provider program to stay hermetic.
  - Assert stdout and exit code.
- `tests/cli/test_init.py`
  - Invoke `voss init my-project`.
  - Assert scaffold files exist.
  - Assert scaffold `.gitattributes` contains `*.voss linguist-language=Voss linguist-detectable=true`.
  - Assert scaffold `.voss` parses.
  - Assert non-empty destination fails without `--force`.
- `tests/packaging/test_entrypoint.py`
  - Use `subprocess.run([sys.executable, "-m", "pip", "install", "-e", "."], cwd=repo_root, ...)` in an isolated venv if feasible.
  - Simpler alternative: run this as an executable plan verification command rather than a pytest test if venv setup is too slow for default tests.
  - Assert `voss --help` succeeds after editable install.
- `tests/tooling/test_linguist_assets.py`
  - Assert top-level `.gitattributes` exists and has the required line.
  - Assert `samples/*.voss` exists and each sample parses.
  - Assert language metadata has extension `.voss`, type `programming`, a color, and parent/group fallback.

Fixture shapes:

- `hello.voss` scaffold:

```voss
fn main() -> string {
  return "Hello from Voss"
}

print(main())
```

This may need to be adjusted to Phase 4's async top-level behavior. Keep it aligned with actual parser/codegen contracts.

- `check_probable.voss`:

```voss
fn f() -> string {
  let intent: probable<string> = ask("classify")
  return intent.value
}
```

Expected: ANLY001 under strict Phase 3 semantics.

- `classify.voss`, `support.voss`, `research.voss` samples should be the same representative examples used by Phase 4 and Phase 6, avoiding multiple diverging copies if possible. If duplication is unavoidable, tests should parse all copies to catch drift.

Verification commands for Phase 5 plans:

- `pytest tests/cli -q`
- `pytest tests/tooling -q`
- `pytest tests/parser tests/analyzer tests/codegen tests/cli tests/tooling -q`
- `python3 -m pip install -e . && voss --help`
- `voss init /tmp/voss-smoke && voss check /tmp/voss-smoke/hello.voss && voss ast /tmp/voss-smoke/hello.voss`

## Risks, Sequencing, Blockers, Dependencies

Main blockers:

- Phase 3 analyzer exports do not exist yet.
- Phase 4 codegen exports do not exist yet.
- Parser example `.voss` fixtures do not exist yet, though parser source is partially implemented.
- No `.voss` samples exist today.

Main risks:

- CLI accidentally duplicates compiler logic. Prevent this with the Phase 5 contract gate and thin wrapper architecture.
- `voss check` writes `.voss-cache` files if it calls analyzer with index emission enabled. Set `emit_indexes=False`.
- `voss run` executes generated code in-process and leaks imports/global state into tests. Use subprocess.
- Editable install tests become slow or mutate the developer environment. Prefer a temporary venv for packaging tests or keep install checks as plan-level verification commands.
- Linguist expectations are easy to overstate. `.gitattributes` can document the intended language, but GitHub will not count unknown languages as native Voss until Linguist has a `languages.yml` entry.
- Scaffold templates become stale if Phase 4 async/top-level behavior changes. Parse/compile scaffold in tests.
- Package data can silently work in editable mode but fail in wheel/sdist. Add at least one package-data/install check.

Recommended sequencing:

1. Contract gate and CLI shell.
   - Verify `phase5-cli-contract-ok`.
   - Add `voss/cli.py`, Click group, help tests, and `[project.scripts]`.
2. Read-only/debug commands.
   - Implement `ast` and `check` first. They exercise parser/analyzer contracts without running generated code.
3. Compile command.
   - Wire parse -> analyze -> generate -> write. Add output-path and diagnostics tests.
4. Run command.
   - Reuse compile pipeline and execute generated Python via subprocess.
5. Init scaffolding.
   - Add templates/package data and scaffold tests.
6. Linguist/tooling assets.
   - Add top-level `.gitattributes`, `samples/`, and language metadata tests. This can run in parallel with init only if ownership is clear.
7. Packaging/install verification.
   - Run editable install and entrypoint checks after CLI and package data are in place.

## Validation Architecture

Nyquist-style validation is applicable because Phase 5 has multiple independent correctness dimensions: compiler orchestration, command UX, packaging/install behavior, scaffold correctness, and Linguist/tooling assets.

Validate across these dimensions:

- **Contract readiness:** Phase 5 cannot start until parser/analyzer/codegen public APIs and example fixtures exist.
- **Command discovery:** installed `voss` executable and `python3 -m voss.cli` expose the same command group and help.
- **Pipeline integrity:** `compile`/`run` call parser, analyzer, and codegen once each through public APIs, without fallback implementations.
- **Diagnostic fidelity:** `check` and `compile` display analyzer diagnostics with file path and line/column; warning/error exit behavior is deterministic.
- **No side effects in check/ast:** `check` and `ast` do not write generated Python or `.voss-cache` artifacts.
- **Generated execution isolation:** `run` executes generated Python in a subprocess and returns its exit code.
- **Package data:** installed package includes `grammar.lark`, `py.typed`, and scaffold templates if templates are file-based.
- **Scaffold validity:** `voss init` output parses, checks, and includes `.gitattributes`.
- **Linguist assets:** repo-level `.gitattributes`, `samples/`, and language metadata exist and are internally consistent.
- **Hermetic default tests:** no live providers, API keys, network, model downloads, or persistent `.voss-cache` artifacts.

## Don't Hand-Roll

- Do not hand-roll CLI parsing. Use Click.
- Do not duplicate parser/analyzer/codegen behavior in `voss/cli.py`.
- Do not invent a second AST printer. Use `to_dict`.
- Do not parse diagnostic strings to determine CLI behavior. Use `Diagnostic` fields and `AnalysisResult.ok`.
- Do not execute generated code in-process for `voss run`.
- Do not add a custom package installer/test harness when `pip install -e .` and `[project.scripts]` cover the requirement.
- Do not claim native GitHub Linguist support before upstream registration.

## Common Pitfalls

- Missing `[project.scripts]`, causing `python3 -m voss.cli` to work but `voss` to be absent after install.
- Forgetting package data for templates, so `voss init` works in the repo but fails from an installed wheel.
- `check` creating `.voss-cache` indexes because it calls analyzer with default `emit_indexes=True`.
- `compile` ignoring analyzer errors and emitting Python anyway.
- `run` swallowing generated process failures instead of returning the subprocess exit code.
- Writing scaffold files into a non-empty directory without explicit `--force`.
- Adding only a hello-world sample to `samples/`; upstream Linguist wants representative real-world code.
- Expecting `.gitattributes linguist-language=Voss` to count as native Voss before `languages.yml` contains Voss.

## Planner Checklist

- [ ] Add `05-01-0` contract gate and require `phase5-cli-contract-ok`.
- [ ] Decide whether warning-only `voss check` exits `0` by default. Recommendation: yes, with `--warnings-as-errors`.
- [ ] Decide template storage: package files under `voss/templates/init/` vs inline strings. Recommendation: package files.
- [ ] Decide language metadata path. Recommendation: `language-metadata/voss.yml`.
- [ ] Decide whether samples duplicate PRD/parser examples or whether one canonical sample directory is referenced by tests. Recommendation: canonical `samples/` plus parser/codegen tests that read from it only if prior phases allow.
- [ ] Add CLI tests before command implementation.
- [ ] Add install/entrypoint verification after `[project.scripts]`.
- [ ] Keep all default tests hermetic and cleanup `.voss-cache`.

---

**Research status:** Ready for Phase 5 planning after Phase 3 and Phase 4 contracts are implemented.
