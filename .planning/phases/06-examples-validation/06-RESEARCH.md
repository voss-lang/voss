---
phase: 06
slug: examples-validation
type: research
created: 2026-05-08
requirements:
  - EX-01
  - EX-02
  - EX-03
---

# Phase 06 - Examples Validation Research

## Scope

Phase 6 proves the v1 pipeline with the three PRD section 7 programs:

- EX-01: `classify.voss`
- EX-02: `support.voss`
- EX-03: `research.voss`

Success means each example passes `voss check`, runs through `voss run`, and also round-trips through `voss compile` followed by `python3` with behavior matching the raw Python equivalents under deterministic CI stubs or optional live providers.

## Current Repo Facts

- Runtime exists and exports the expected Phase 1 public surface from `voss_runtime/__init__.py`, including `ProbableValue`, `ContextScope`, `BudgetScope`, `SemanticMatcher`, `VossAgent`, `gather`, memory classes, `tool`, provider config helpers, and `StubProvider`.
- Raw Python semantic targets exist:
  - `examples/raw_python/classify.py`
  - `examples/raw_python/support.py`
  - `examples/raw_python/research.py`
- Parser examples exist and match PRD section 7 source:
  - `tests/parser/examples/classify.voss`
  - `tests/parser/examples/support.voss`
  - `tests/parser/examples/research.voss`
- Parser golden tests exist in `tests/parser/test_examples.py`.
- Analyzer exists in `voss/analyzer.py`; diagnostics/index result types exist in `voss/diagnostics.py`; public exports exist in `voss/__init__.py`.
- Analyzer example tests exist in `tests/analyzer/test_examples.py`; support emits a fake `.voss-cache/support.idx` manifest under `tmp_path`.
- Codegen API exists in `voss/codegen.py`, but current implementation only handles import collection and empty/import-only programs. It does not yet lower functions, ctx, match, agents, `within/fallback`, or top-level executable statements.
- Codegen tests currently cover writer/import basics only: `tests/codegen/test_writer.py`, `tests/codegen/test_imports.py`. The planned `tests/codegen/test_examples.py` and snapshots are absent.
- Phase 5 CLI/package surfaces are absent in the current tree: no `voss/cli.py`, no `[project.scripts]` entry, no `tests/cli/`, no `tests/packaging/`, no `tests/tooling/`, no `samples/`, and no repo-level `.gitattributes`.
- No repo-local `.voss-cache/*.idx` artifacts were found during research.
- Graphify query was attempted, but `graphify-out/graph.json` does not exist for this repo, so this research used planning docs and targeted source inspection.

## Contract Gaps

Phase 6 must not start e2e validation until these gaps are closed:

- Phase 4 is not complete enough for examples. `generate_python()` currently cannot emit runnable Python for any PRD section 7 example.
- Phase 4 example parity tests from `04-06-PLAN.md` are not present.
- Phase 5 is not implemented. The literal `voss check`, `voss compile`, and `voss run` commands cannot be validated yet.
- CI subprocess execution has no obvious default-model configuration knob. Runtime registers `__stub__`, but `RuntimeConfig.default_model` defaults to `claude-sonnet-4-5`, and no env-var config path is visible. Phase 6 needs a deterministic child-process provider contract before `voss run` and `python3 generated.py` can be hermetic.
- `SemanticMatcher.from_index()` still expects a single-match index schema, while analyzer emits a program manifest with `matches`. Codegen must consume the manifest or provide a runtime-compatible helper before `support.voss` can avoid model downloads.

## Phase 6 Contract Gate

Add a first read-only gate before any example tests or source edits. The gate should be recorded by the executor and must print:

```text
phase6-examples-contract-ok
```

Recommended checks:

```bash
python3 - <<'PY'
from pathlib import Path
import importlib
import tomllib

runtime = importlib.import_module("voss_runtime")
runtime_exports = [
    "ProbableValue", "ContextScope", "BudgetScope", "BudgetExceededError",
    "SemanticMatcher", "VossAgent", "gather", "EpisodicMemory",
    "SemanticMemory", "WorkingMemory", "tool", "StubProvider",
    "configure", "reset_config",
]
missing_runtime = [name for name in runtime_exports if not hasattr(runtime, name)]

voss = importlib.import_module("voss")
compiler_exports = [
    "parse", "to_dict", "analyze", "AnalysisResult", "Diagnostic",
    "EmittedIndex", "generate_python", "CodegenResult", "CodegenError",
]
missing_compiler = [name for name in compiler_exports if not hasattr(voss, name)]

required_files = [
    Path("tests/parser/examples/classify.voss"),
    Path("tests/parser/examples/support.voss"),
    Path("tests/parser/examples/research.voss"),
    Path("examples/raw_python/classify.py"),
    Path("examples/raw_python/support.py"),
    Path("examples/raw_python/research.py"),
    Path("tests/analyzer/test_examples.py"),
    Path("tests/codegen/test_examples.py"),
    Path("voss/cli.py"),
    Path("samples/classify.voss"),
    Path("samples/support.voss"),
    Path("samples/research.voss"),
]
missing_files = [str(path) for path in required_files if not path.exists()]

pyproject = tomllib.loads(Path("pyproject.toml").read_text())
scripts = pyproject.get("project", {}).get("scripts", {})
missing_script = scripts.get("voss") != "voss.cli:main"

if missing_runtime or missing_compiler or missing_files or missing_script:
    raise SystemExit(
        "Phase 6 contract incomplete; "
        f"missing_runtime={missing_runtime}; "
        f"missing_compiler={missing_compiler}; "
        f"missing_files={missing_files}; "
        f"missing_voss_script={missing_script}"
    )

print("phase6-examples-contract-ok")
PY
```

Also require that Phase 5 recorded `phase5-cli-contract-ok`, because Phase 6 depends on installed CLI behavior rather than direct internal calls.

## E2E Validation Approach

Create `tests/examples/` as the Phase 6 test package. Keep shared helpers test-local.

Recommended helper responsibilities:

- Copy the three `.voss` examples into a `tmp_path` project to avoid modifying parser fixtures.
- Run CLI commands through subprocess or Click runner exactly as Phase 5 tests do.
- Compile into `tmp_path/out/*.py`, not beside repo fixtures.
- Configure deterministic provider behavior for generated Python child processes through the provider contract established by Phase 5/6.
- Load raw Python equivalents and generated modules for direct function-level parity where subprocess stdout is too coarse.
- Assert no `.voss-cache/*.idx` or generated `.py` appears under the repo root.

For each example, validate this matrix:

| Example | `voss check` | `voss compile` + `python3` | `voss run` | Raw Python parity |
| --- | --- | --- | --- | --- |
| `classify.voss` | no errors | stdout `cancel_subscription`; low-confidence path `unknown` via function-level test | same stdout | compare to `examples.raw_python.classify.classify_intent` |
| `support.voss` | no errors | angry/refund/auth/fallback routes match | same representative stdout | compare to `examples.raw_python.support.handle_message` |
| `research.voss` | no errors | happy path returns non-empty stub summary; timeout fallback joins four reports | same representative stdout | compare to `examples.raw_python.research.run_research` |

The CLI tests should exercise the real commands:

```bash
voss check classify.voss
voss compile classify.voss -o /tmp/.../classify.py
python3 /tmp/.../classify.py
voss run classify.voss
```

Repeat for `support.voss` and `research.voss`.

## Deterministic CI Path

Default tests must use `StubProvider` and fake semantic embeddings. They must not require API keys, live provider calls, network, sentence-transformers downloads, ChromaDB persistence outside temp dirs, or Ollama models.

Recommended CI behavior:

- Classify: use `StubProvider(default_response="cancel_subscription")` and a second direct function-level case with `default_response=""`.
- Support: avoid real sentence-transformers by using analyzer fake index cases and generated/runtime matcher construction with explicit embeddings, or monkeypatch `SemanticMatcher._encode` before importing generated/raw modules.
- Research: use `StubProvider(default_response="STUB SUMMARY")`; monkeypatch generated `Synthesizer.run` or budget helper in function-level tests to force fallback.
- For subprocess CLI tests, require a supported deterministic provider knob. Acceptable contracts:
  - CLI option such as `--model __stub__` passed through to generated process.
  - Environment variable consumed by runtime startup, such as `VOSS_DEFAULT_MODEL=__stub__`.
  - Generated examples include a test-only configuration hook when run under an explicit CI env flag.

If no child-process stub knob exists after Phase 5, Phase 6 should fail the contract gate rather than silently using live defaults.

## Optional Live Provider Path

Live tests are optional and should prove the same commands against real providers only when explicitly requested.

Rules:

- Mark every live test with `@pytest.mark.live`.
- Skip unless provider configuration and credentials are explicitly present.
- Do not run live tests in default `pytest` or CI.
- Do not assert exact natural-language output. Assert command success, non-empty output, expected route shape when deterministic, and absence of tracebacks.
- Record provider/model/date and sanitized output summary in the Phase 6 execution summary.

Suggested command:

```bash
pytest tests/examples -q -m live
```

## Cache And Artifact Safety

Analyzer index emission must stay project-local and temp-dir scoped.

- Use `project_root=tmp_path` and `cache_dir=".voss-cache"` for analyzer/compiler helpers.
- For CLI subprocesses, set cwd to the copied temp project, not the repo root.
- Compile outputs should go under `tmp_path/out/`.
- `voss check` must use `emit_indexes=False` and must not create `.voss-cache`.
- `voss compile` may create `.voss-cache/<program>.idx` only under the temp project.
- After each test and at suite end, scan the repo root for `**/.voss-cache/*.idx` excluding pytest temp internals and fail if any are found.
- Do not snapshot temp absolute paths in generated output comparisons.

Recommended cleanup check:

```bash
python3 - <<'PY'
from pathlib import Path
bad = [str(p) for p in Path(".").glob("**/.voss-cache/*.idx") if ".pytest_cache" not in p.parts]
if bad:
    raise SystemExit(f"repo-local indexes left behind: {bad}")
print("phase6-no-repo-local-cache-ok")
PY
```

## Likely Test Files

- `tests/examples/__init__.py`
- `tests/examples/helpers.py`
- `tests/examples/test_contract.py`
- `tests/examples/test_classify_e2e.py`
- `tests/examples/test_support_e2e.py`
- `tests/examples/test_research_e2e.py`
- `tests/examples/test_cli_matrix.py`
- Optional: `tests/examples/test_live_examples.py`

Phase 6 should read but not edit:

- `tests/parser/examples/*.voss`
- `examples/raw_python/*.py`
- `tests/integration/test_*_example.py`
- `tests/codegen/test_examples.py`
- `tests/cli/*`
- `voss/cli.py`
- `voss/codegen.py`
- `voss/analyzer.py`
- `voss_runtime/*`

If Phase 6 discovers missing behavior in CLI/codegen/runtime, record the blocker and route it to the owning phase surface. Do not patch parser/analyzer/codegen fallbacks inside example tests.

## Verification Commands

Focused:

```bash
pytest tests/examples/test_contract.py -q
pytest tests/examples/test_classify_e2e.py -q
pytest tests/examples/test_support_e2e.py -q
pytest tests/examples/test_research_e2e.py -q
pytest tests/examples/test_cli_matrix.py -q
```

Phase-level:

```bash
pytest tests/examples -q
pytest tests/parser tests/analyzer tests/codegen tests/cli tests/examples -q
python3 -m pip install -e . && voss --help
```

Optional live:

```bash
pytest tests/examples -q -m live
```

Artifact safety:

```bash
python3 - <<'PY'
from pathlib import Path
bad = [str(p) for p in Path(".").glob("**/.voss-cache/*.idx") if ".pytest_cache" not in p.parts]
if bad:
    raise SystemExit(f"repo-local indexes left behind: {bad}")
print("phase6-no-repo-local-cache-ok")
PY
git diff --check -- tests/examples
```

## Sequencing

1. Contract gate
   - Verify Phase 1 runtime, Phase 2 parser examples, Phase 3 analyzer exports, Phase 4 codegen API/example tests, and Phase 5 CLI/entrypoint/samples.
   - Marker: `phase6-examples-contract-ok`.
2. Shared harness
   - Build temp-project copy, CLI runner, subprocess runner, raw/generated parity helpers, stub provider setup, and cache scan.
3. Classify wave
   - Cover confident and low-confidence outputs through direct function parity plus CLI check/compile/run.
4. Support wave
   - Cover semantic route labels and fallback ctx path with fake embeddings/indexes.
5. Research wave
   - Cover spawn/gather happy path and `within/fallback` timeout path.
6. Full matrix
   - Run all three programs through all commands after editable install. Add optional live-provider tests gated by `live`.

## Risks

- Codegen incompleteness is the largest current blocker.
- CLI absence blocks all literal Phase 6 success criteria.
- Stub configuration for subprocesses is unresolved. Without a child-process provider knob, default examples may hit `LiteLLMProvider`.
- Semantic index schema mismatch can make `support.voss` load embeddings incorrectly or download a model at runtime.
- Research fallback is timing-sensitive. Tests should monkeypatch a short budget or synthesizer delay rather than rely on wall-clock flakiness.
- Natural-language provider output is not stable. Default tests must assert deterministic stub output; live tests should avoid exact text comparisons.

## Nyquist Validation Dimensions

- Pipeline coverage: parse, analyze/check, codegen, Python execution, CLI run.
- Example coverage: classify, support, research each independently validated.
- Behavior parity: generated behavior compared to raw Python equivalents, not only stdout smoke.
- Provider mode: deterministic stub by default; optional live provider path separately marked.
- Semantic routing: support validates each route and fallback, with no embedding downloads.
- Budget behavior: research validates both success and fallback paths.
- Artifact hygiene: all indexes and generated Python live under temp dirs; repo root remains clean.
- Packaging reality: installed `voss` entrypoint is tested, not only source-tree imports.
- Failure visibility: missing upstream contracts fail the Phase 6 gate with concrete missing symbols/files.

## Threat Model Notes

- T-06-A: E2E tests pass by using direct internal APIs while the CLI is broken.
  - Mitigation: matrix must include installed or subprocess `voss check`, `voss compile`, and `voss run`.
- T-06-B: Tests accidentally call live providers or download embedding models.
  - Mitigation: default suite uses `StubProvider`, fake indexes, monkeypatches where needed, and no `live` marker.
- T-06-C: Generated output diverges from raw Python behavior.
  - Mitigation: compare generated calls to `examples/raw_python/*` for each important branch.
- T-06-D: `.voss-cache` or generated files leak into the repo.
  - Mitigation: temp cwd/project roots plus explicit repo-root artifact scan.
- T-06-E: Live-provider tests become flaky correctness gates.
  - Mitigation: live tests are opt-in, marked, and assert only shape/success.

## RESEARCH COMPLETE

File written: `.planning/phases/06-examples-validation/06-RESEARCH.md`
