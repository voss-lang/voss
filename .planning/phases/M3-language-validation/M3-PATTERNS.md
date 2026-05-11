# Phase M3: Language Validation - Pattern Map

**Mapped:** 2026-05-11
**Files analyzed:** 22 (7 new, 13 modified, 2 deleted)
**Analogs found:** 22 / 22 (every M3 file has a direct sibling in tree)

M3 is overwhelmingly a wiring + sample-extension + framing phase. Per `M3-RESEARCH.md §Summary`, the parser/analyzer/codegen/runtime stack already supports every construct M3 adds. Patterns below cite the closest analog by `file:line` and quote the lines to copy.

---

## File Classification

### New files (7)

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|----------------|---------------|
| `tests/examples/test_check_speed.py` | test (perf + sentinel) | request-response (subprocess) + introspection | `tests/cli/test_check.py:70-97` (cache-leak invariant) + `tests/examples/test_cli_matrix.py` (subprocess wall-clock pattern) | role-match |
| `tests/cli/test_run_stub_fallback.py` | test (CLI banner + behavior) | request-response (Click + subprocess) | `tests/cli/test_run.py:36-78` (Click `CliRunner` + monkeypatched `subprocess.run`) | exact |
| `tests/parser/examples/coverage/memory_semantic.voss` | fixture (parser golden) | static | `tests/parser/examples/assistant.voss:1-18` (memory.episodic + memory.semantic + use, sole reference for `memory.*` syntax) | exact |
| `tests/parser/examples/coverage/memory_working.voss` | fixture (parser golden) | static | `tests/parser/examples/assistant.voss:1-18` | exact |
| `tests/analyzer/examples/coverage/` (mirror or runner) | fixture + parametrized runner | static | `tests/analyzer/test_examples.py:1-85` (`_load()` + `analyze(...)` + assert no specific diag codes) | exact |
| `tests/codegen/snapshots/coverage/` (snapshot mirrors) | fixture + snapshot test | transform (codegen) | `tests/codegen/test_snapshots.py:14-71` (`_generated_sources` + `_assert_readable_snapshot`) | exact |
| `docs/voss-vs-python.md` | docs (deliverable) | static | New top-level doc; no analog in tree. Pattern source: README.md "Quickstart" code-block style + `examples/raw_python/*.py` paired side-by-side. | none (greenfield) |

### Modified files (13)

| Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---------------|------|-----------|----------------|---------------|
| `voss/analyzer.py` (`_visit_match_stmt` ~479-501) | analyzer rule (static check guard) | transform | Self — gate on the existing `emit_indexes` flag (analyzer.py:204-211, 435) | exact (in-file) |
| `voss/cli.py` (`run` ~170-201; `check` ~204-228) | CLI command (Click) | request-response | `voss/harness/cli.py:38-77` `_resolve_auth_or_die` (canonical `auth.resolve` consumer + stderr banner via `click.echo(..., err=True)`) | role-match |
| `voss_runtime/providers/__init__.py` (and/or `voss_runtime/_config.py`) | runtime hook (provider dispatch) | request-response | Self — `providers.get()` already chooses by `default_model`; add env-var conditional | exact (in-file) |
| `samples/support.voss` | sample (.voss source) | static | `tests/parser/examples/assistant.voss:1-2,5-17` (memory.episodic declaration + `.add(...,role:)` + `.last(N)` pattern) | exact |
| `samples/research.voss` | sample (.voss source) | static | `tests/parser/examples/assistant.voss:3` (`use` import) + `voss/grammar.lark:133` (`try_stmt`) + `tests/codegen/test_imports.py:71-90` (`use voss_runtime::tools::tool`) | exact |
| `samples/classify.voss` | sample (.voss source) | static | Self — only a header comment prepend | exact |
| `examples/raw_python/support.py` | sample parity oracle (raw Python) | event-driven (async) | Self + new `EpisodicMemory` import from `voss_runtime/memory/episodic.py:1-67` | exact (in-file) |
| `examples/raw_python/research.py` | sample parity oracle (raw Python) | event-driven (async) | Self — already has one `try/except BudgetExceededError` at lines 54-60; add a second `try/except` around `web_search` | exact (in-file) |
| `tests/examples/helpers.py` (lines 22-39) | test helper (fixture loader) | request-response | Self — flip `PARSER_EXAMPLES` constant to a `SAMPLES_DIR = REPO_ROOT / "samples"` | exact (in-file) |
| `tests/examples/test_support_e2e.py` | test (e2e + raw parity) | request-response + event-driven | Self (test_support_e2e.py:194-225 voss-run-matches-compile pattern) + raw-parity assert at 144-151 | exact (in-file) |
| `tests/examples/test_research_e2e.py` | test (e2e + raw parity) | request-response + event-driven | Self (test_research_e2e.py:112-134 raw-parity pattern) | exact (in-file) |
| `README.md` | docs (top-level) | static | Self — rewrite intro paragraph + add section linking new doc; mirror existing "Project Docs" link list | exact (in-file) |

### Deleted files (2)

| Deleted File | Reason | Per Decision |
|--------------|--------|--------------|
| `tests/examples/test_helpers.py` | Meta-tests on the helpers themselves are overkill for v0.1 | D-09 |
| `tests/examples/test_live_examples.py` | Live verification stays manual; no `--live` opt-in path | D-09 |

---

## Pattern Assignments

### `voss/analyzer.py` (modify `_visit_match_stmt`) — D-03 static-only check

**Analog:** Self. The existing `emit_indexes` flag (set at analyzer.py:204-211 init + read at 435 for manifest write) must also gate `build_cases`.

**Current shape** (analyzer.py:479-501):
```python
def _visit_match_stmt(self, match: MatchStmt) -> None:
    self._infer_expr(match.scrutinee)
    similar_pairs: list[tuple[str, str]] = []
    for ordinal, case in enumerate(match.cases):
        if isinstance(case.pattern, SimilarPattern):
            label = f"case_{ordinal}"
            similar_pairs.append((case.pattern.text, label))
        for s in case.body:
            self._visit_stmt(s)
    if not similar_pairs:
        return
    if self.index_builder is None:
        self.index_builder = SemanticMatcherIndexBuilder()       # <-- D-03 violation: eager HF load via __init__/_encode
    built = self.index_builder.build_cases(similar_pairs)
    threshold = match.threshold if match.threshold is not None else 0.75
    match_id = f"match_{match.span.line_start}_{match.span.col_start}"
    self._match_entries.append(
        {"match_id": match_id, "threshold": threshold, "cases": built}
    )
```

**Adaptation notes:**
- Insert an `emit_indexes=False` early-return that still records a `_match_entries` row with `"cases": []` (so static signature validation remains visible), then `return`. Encoder is never instantiated when `voss check` runs.
- Do NOT touch `_emit_program_index` (analyzer.py:641-719): that path is already gated by `emit_indexes` at line 435.
- Preserve scrutinee inference + per-case body walk (lines 480-487) — those are the "static signature validation" CONTEXT D-03 promises.
- Pattern shape per `M3-RESEARCH.md §Pattern 2`.

---

### `voss/cli.py` (modify `run` ~170-201) — D-01 auto-stub + D-02 banner

**Analog:** `voss/harness/cli.py:38-77` `_resolve_auth_or_die` — canonical `auth.resolve(preference="auto")` consumer + Click stderr banner pattern.

**Imports + resolver call pattern** (harness/cli.py:38-50, condensed):
```python
import click
from voss.harness import auth as auth_mod

def _resolve_auth_or_die(preference: str) -> tuple[auth_mod.Resolution, ModelProvider]:
    res = auth_mod.resolve(preference)
    if res.source == "none":
        click.echo(
            f"no usable credentials ({res.detail}). try one of:\n"
            "  • export ANTHROPIC_API_KEY=... (or OPENAI_API_KEY)\n"
            "  • ...",
            err=True,
        )
        sys.exit(2)
```

**Resolver return shape** (harness/auth.py:323-330):
```python
@dataclass
class Resolution:
    source: str  # "env-anthropic" | "env-openai" | "claude-oauth" | "codex" | "codex-oauth" | "none"
    detail: str
    ...
```

**Existing `run` skeleton to extend** (voss/cli.py:170-201):
```python
@main.command("run")
@click.argument("source", type=click.Path(path_type=Path))
@click.option("--cache-dir", "cache_dir", type=click.Path(path_type=Path), default=Path(".voss-cache"))
...
def run(source, cache_dir, project_root, verbose):
    with tempfile.TemporaryDirectory(prefix="voss-run-") as tmp:
        ...
        completed = subprocess.run(
            [sys.executable, str(generated)],
            capture_output=True,
            text=True,
        )                                          # <-- inject env= before this call
```

**Adaptation notes:**
- Before `subprocess.run(...)`, call `auth_mod.resolve(preference="auto")`. If `res.source == "none"` OR `os.environ.get("VOSS_HERMETIC") == "1"`:
  - `click.echo("voss: no provider creds detected — using __stub__ (deterministic fake responses)", err=True)` (D-02; banner is hard-coded, no interpolation).
  - Build `env = os.environ.copy(); env["VOSS_HERMETIC"] = "1"` and pass `env=env` to `subprocess.run`.
- Otherwise pass `env=None` (inherit unchanged).
- M3-RESEARCH §Pattern 1 + §Pitfall 1 + §Pitfall 5 cover the exact shape; banner must route to `err=True` so subprocess `result.stderr` (not `result.output`) captures it.

---

### `voss_runtime/providers/__init__.py` — D-01 auto-stub detection

**Analog:** Self. The current `get()` (providers/__init__.py:12-18) already routes by `default_model`; add a one-line env-var precedence check.

**Current shape** (providers/__init__.py:12-22):
```python
def get(name: str | None = None) -> ModelProvider:
    from voss_runtime._config import get_config

    key = name or get_config().default_model
    if key in _registry:
        return _registry[key]
    return _registry.get("__default__", LiteLLMProvider())


register("__default__", LiteLLMProvider())
register("__stub__", StubProvider())
```

**Adaptation notes:**
- Smallest-diff path (per M3-RESEARCH §Open Question Q-2): inside `get()`, if `name is None` AND `os.environ.get("VOSS_HERMETIC") == "1"`, force `key = "__stub__"` before the registry lookup.
- Leave explicit `name` overrides untouched — test code that passes `get("foo")` still wins.
- `import os` at top of file (currently absent) is the only new import.

---

### `samples/support.voss` — D-05 + D-14

**Analog:** `tests/parser/examples/assistant.voss:1-2, 5-17` — only in-tree reference for `memory.episodic` + `.add(..., role:)` + `.last(N)`.

**Reference excerpt** (assistant.voss:1-17):
```voss
# assistant.voss
let history: memory.episodic(capacity: 20 turns)
let kb: memory.semantic(source: "./knowledge_base/")

fn chat(userMessage: string) -> string {
    history.add(userMessage, role: "user")

    let relevant = kb.retrieve(userMessage, top_k: 3)

    ctx(budget: 4000 tokens) {
        include history.last(6)
        include relevant

        let response: probable<string> = ask(userMessage)
        history.add(response.value, role: "assistant")
        yield response.value
    }
}
```

**Codegen lowering** (codegen.py:690-705 `_emit_memory_let`):
```python
# memory.episodic(capacity: N turns)  →  EpisodicMemory(capacity=N)
```

**Target shape** (per M3-RESEARCH §"Pattern: extend samples/support.voss"):
```voss
# support.voss — prompt block, match similar (semantic routing),
# ctx(budget: N tokens), memory.episodic.
prompt SupportAgent { "..." }

let tickets: memory.episodic(capacity: 50 turns)

fn handleMessage(userMessage: string) -> string {
    tickets.add(userMessage, role: "user")
    match userMessage {
        case similar(...) => { ... }
        case _ => {
            ctx(budget: 3000 tokens) {
                include tickets.last(6)
                yield ask(userMessage)
            }
        }
    }
}
```

**Adaptation notes:**
- Add header comment per D-14 (second `#` line listing primitives).
- Add `let tickets: memory.episodic(capacity: 50 turns)` at module scope (mirrors `let history` in assistant.voss:2).
- Add `tickets.add(userMessage, role: "user")` at fn entry and `include tickets.last(6)` inside the wildcard `ctx` (mirrors assistant.voss:6, 11).
- Do NOT add a `model:` annotation (M3-RESEARCH §Q-4): keeps auto-stub fallback working.

---

### `samples/research.voss` — D-06 + D-14

**Analog:** `tests/codegen/test_imports.py:71-90` (verifies `use voss_runtime::tools::tool` codegens correctly) + `voss/grammar.lark:133` (`try_stmt`).

**`use` codegen contract** (codegen.py:142-148 via test_imports.py:71-77):
```python
# `use voss_runtime::tools::tool`  →  `from voss_runtime.tools import tool`
```

**`try/catch` grammar** (grammar.lark:133):
```
try_stmt: "try" block "catch" [NAME] block
```

Parser accepts both `try { } catch { }` and `try { } catch e { }` (parser.py:542-557).

**Target shape** (per M3-RESEARCH §"Pattern: extend samples/research.voss"):
```voss
# research.voss — agent, spawn, gather, ctx, within/fallback, try/catch, use.
use voss_runtime::tools::tool

agent Researcher(topic: string) -> string {
    system: "..."
    tools: [webSearch]

    ctx(budget: 2000 tokens) {
        try {
            let results = webSearch(topic, max_results: 5)
            include results
        } catch e {
            include "web search unavailable"
        }
        yield ask("Summarize the key findings on: " + topic)
    }
}
...
```

**Adaptation notes:**
- Add header comment per D-14.
- Prepend `use voss_runtime::tools::tool` (NOT the literal "use voss.tools" from CONTEXT D-06 — see M3-RESEARCH §Pitfall 1 + §Open Question Q-1). The `::` separator is mandatory per grammar.lark:175.
- Wrap the `webSearch(...)` call in `try { ... } catch e { ... include "web search unavailable" }`. Network call is the natural failure point.
- Do NOT add `model:` annotations.

---

### `samples/classify.voss` — D-14 only

**Analog:** Self. Only a header comment prepend.

**Adaptation notes:** Add a second `#` line listing primitives (e.g., `# classify.voss — probable<T>, confidence gate (@ p >= 0.80), implicit ctx fallback.`). Body unchanged.

---

### `examples/raw_python/support.py` — D-12 parity

**Analog:** Self + `voss_runtime/memory/episodic.py:1-67` (EpisodicMemory API: `add(text, role=...)`, `last(n)`, `render()`).

**Current imports + class refs** (support.py:1-17):
```python
from voss_runtime import ContextScope, SemanticMatcher

matcher = SemanticMatcher(
    cases=[...],
    threshold=0.55,
)
```

**Adaptation notes:**
- Import `EpisodicMemory` from `voss_runtime` (already exported per voss_runtime/__init__.py:21).
- Construct a module-scope `tickets = EpisodicMemory(capacity=50)` mirroring the `.voss` source.
- Inside `handle_message`, call `tickets.add(user_message, role="user")` at entry and `await ctx.add(tickets.render(last=6))` (or `"\n".join(tickets.last(6))` — match whatever the codegen output uses) inside the `ContextScope` fallback branch.
- The e2e parity assertion (`test_support_e2e.py:147-151`) requires stdout to match byte-for-byte under same StubProvider seed. Per M3-RESEARCH §Pitfall 7, edit this file in the SAME plan task as the sample extension.

---

### `examples/raw_python/research.py` — D-12 parity

**Analog:** Self. The file already has one `try/except BudgetExceededError` at lines 54-60 (parity for `within budget ... fallback`); D-06 adds a second `try/except Exception` around `web_search`.

**Existing try/except pattern** (research.py:54-60):
```python
try:
    synth = Synthesizer().spawn(reports)
    return await run_with_budget(
        synth.result(), token_limit=5000, latency_ms=10_000
    )
except BudgetExceededError:
    return "\n---\n".join(reports)
```

**Adaptation notes:**
- Add `try/except Exception:` around the `results = web_search(topic, max_results=5)` call inside `Researcher.run` (research.py:27-30). Fallback should write `"web search unavailable"` to the ContextScope to match the `.voss` source.
- No new imports.

---

### `tests/examples/helpers.py` (lines 22-39) — D-09 repoint

**Analog:** Self.

**Current shape** (helpers.py:22-39):
```python
REPO_ROOT = Path(__file__).resolve().parents[2]
PARSER_EXAMPLES = REPO_ROOT / "tests" / "parser" / "examples"


def example_source(name: str) -> Path:
    """Return path to a canonical parser example .voss source."""
    path = PARSER_EXAMPLES / f"{name}.voss"
    if not path.exists():
        raise FileNotFoundError(f"parser example missing: {path}")
    return path


def copy_example(tmp_path: Path, name: str) -> Path:
    """Copy a parser example into ``tmp_path`` and return the destination."""
    src = example_source(name)
    dest = tmp_path / src.name
    shutil.copyfile(src, dest)
    return dest
```

**Adaptation notes:**
- Rename `PARSER_EXAMPLES` → `SAMPLES_DIR` and repoint to `REPO_ROOT / "samples"`. Per M3-RESEARCH §Pitfall 4, this is the lynchpin: without it the e2e suite still validates legacy `tests/parser/examples/*.voss`, not the canonical `samples/*.voss` post-M3 extension.
- Update both `example_source` and `copy_example` docstrings to say "canonical sample" not "parser example".
- The parser golden tests at `tests/parser/test_examples.py` keep their own `EXAMPLES_DIR = Path(__file__).parent / "examples"` and are unaffected.

---

### `tests/examples/test_support_e2e.py` — D-05 + D-12

**Analog:** Self. Pattern already in file at lines 104-151 (parametrized routing + raw-parity assert) and 194-224 (voss-run-matches-compile).

**Existing raw-parity assertion** (test_support_e2e.py:144-151):
```python
from examples.raw_python.support import handle_message as raw_handle_message

generated_value = asyncio.run(module.handleMessage(user_message))
raw_value = asyncio.run(raw_handle_message(user_message))

assert generated_value == expected_prefix + user_message
assert raw_value == expected_prefix + user_message
assert generated_value == raw_value
```

**Adaptation notes:**
- Tests already source via `copy_example(tmp_path, "support")` (line 54) — after helpers.py is repointed (above), this automatically picks up the extended `samples/support.voss`.
- Add a new test case (or extend `test_support_generic_falls_through_to_stub` at line 154) asserting that the ticket history is preserved between calls. Simplest: call `module.handleMessage(...)` twice and check `tickets.last(2)` contains both messages via a module attribute probe.
- Keep existing in-process `_patch_semantic_matcher_in_process` fixture (line 30-34).

---

### `tests/examples/test_research_e2e.py` — D-06 + D-12

**Analog:** Self. The `try/catch` extension preserves the existing happy/fallback test pair (lines 112-164).

**Adaptation notes:**
- After helpers.py repoint, tests automatically source the extended `samples/research.voss`.
- Add an assertion (extend `test_research_compile_python_happy_path_matches_raw` or new sibling) that the generated Python contains `try:` and `except` (codegen lowering for `try/catch e` per codegen.py:1107-1126).
- Optionally: add a test where `webSearch` raises and confirm both generated and raw produce `"web search unavailable"` in the context — mirrors the BudgetExceededError forcing pattern at lines 145-154.

---

### `tests/examples/test_check_speed.py` (NEW) — D-03 sentinel + D-13 wall-clock

**Analogs:**
- **Wall-clock pattern:** subprocess pattern from `tests/examples/test_cli_matrix.py` + `tests/examples/helpers.py:run_voss` (helpers.py:60-69).
- **Sentinel pattern:** `tests/cli/test_check.py:70-80` (in-process invariant assertion: nothing leaks beyond what's intended).
- **In-process analyze call:** `tests/codegen/test_examples.py:76-93` (`_compile_example` shape: `parse(src) → analyze(program, emit_indexes=False, index_builder=FakeIndexBuilder())`).

**Sentinel pattern reference** (tests/cli/test_check.py:70-80):
```python
def test_check_does_not_emit_indexes_or_cache_files():
    runner = CliRunner()
    with runner.isolated_filesystem() as fs:
        path = _write("clean.voss", _CLEAN_SOURCE)
        result = runner.invoke(
            main, ["check", "--cache-dir", ".voss-cache", str(path)]
        )
        assert result.exit_code == 0, result.output
        fs_path = Path(fs)
        assert not (fs_path / ".voss-cache").exists()
        assert not list(fs_path.glob("**/*.idx"))
```

**Speed test sketch** (M3-RESEARCH §"Pattern: tests/examples/test_check_speed.py"):
```python
import time
from pathlib import Path
import pytest
from tests.examples.helpers import copy_example, run_voss

CHECK_CEILING_SECONDS = 2.0

@pytest.mark.parametrize("sample", ["classify", "support", "research"])
def test_check_speed_under_ceiling(tmp_path, sample):
    copy_example(tmp_path, sample)
    run_voss(["check", f"{sample}.voss"], cwd=tmp_path)        # warmup
    start = time.perf_counter()
    result = run_voss(["check", f"{sample}.voss"], cwd=tmp_path)
    elapsed = time.perf_counter() - start
    assert result.returncode == 0, result.stderr
    assert elapsed < CHECK_CEILING_SECONDS, (
        f"voss check {sample}.voss took {elapsed:.2f}s "
        f"(ceiling {CHECK_CEILING_SECONDS}s) — D-03 regression?"
    )

def test_check_does_not_load_hf_encoder():
    """D-03 sentinel: in-process analyze on support.voss must not import sentence_transformers."""
    from voss import analyze, parse
    src = (Path(__file__).resolve().parents[2] / "samples" / "support.voss").read_text()
    program = parse(src, file="samples/support.voss")
    result = analyze(program, source_path="samples/support.voss", emit_indexes=False)
    assert result.ok
    import sys
    assert "sentence_transformers" not in sys.modules, (
        "D-03 violated: HF sentence_transformers loaded during voss check"
    )
```

**Adaptation notes:**
- Warm-up once per parametrize iteration (M3-RESEARCH §Q-3 recommends warm-only).
- Ceiling is `2.0s` per CONTEXT D-13 starting target; tune up during execution if CI variance demands it, but keep as a real `assert`, not `print(...)`.
- Sentinel test must run BEFORE any test that imports `voss_runtime.semantic` triggers HF; pytest sorts alphabetically inside a file so naming it `test_check_does_not_load_hf_encoder` works.

---

### `tests/cli/test_run_stub_fallback.py` (NEW) — D-01 + D-02

**Analog:** `tests/cli/test_run.py:36-78` — canonical Click-CliRunner + monkeypatch-`subprocess.run` pattern for testing the `voss run` command without actually executing generated code.

**Reference pattern** (test_run.py:22-58):
```python
def _patch_compile(monkeypatch, script_body: str):
    """Replace _compile_source with a stub that writes a known generated script."""
    def fake_compile(source_path, **kwargs):
        output_path = kwargs.get("output_path") or Path(source_path).with_suffix(".py")
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(script_body)
        return Path(output_path)
    monkeypatch.setattr("voss.cli._compile_source", fake_compile)


def test_run_executes_generated_python_with_current_interpreter(monkeypatch):
    _patch_compile(monkeypatch, "print('ok')\n")

    captured: dict = {}
    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        captured["cmd"] = list(cmd)
        captured["env"] = kwargs.get("env")     # <-- M3 addition: capture env to assert VOSS_HERMETIC
        return real_run([sys.executable, "-c", "..."], *args, **kwargs)

    monkeypatch.setattr("voss.cli.subprocess.run", fake_run)
    runner = CliRunner()
    with runner.isolated_filesystem():
        path = _write_source()
        result = runner.invoke(main, ["run", str(path)])
        assert result.exit_code == 0, result.output
```

**Adaptation notes:**
- Two tests at minimum: (a) `test_auto_register_stub_when_no_creds` — monkeypatch `voss.cli.auth_mod.resolve` (or whatever import name `voss/cli.py` adopts) to return `Resolution(source="none", detail="forced")`; assert the captured `env["VOSS_HERMETIC"] == "1"`. (b) `test_stub_fallback_banner_on_stderr` — invoke as above; assert `"no provider creds detected" in result.stderr` (NOT `result.output` — Click routes `err=True` to `.stderr`; M3-RESEARCH §Pitfall 5).
- Use `CliRunner(mix_stderr=False)` if Click version requires it for separate stderr capture.
- Optionally a third test: `VOSS_HERMETIC=1` env-var path. Monkeypatch `os.environ` to set the var; assert banner fires even when `auth_mod.resolve` would have returned a real source.
- Mirror `tests/cli/test_run.py` style (no pytest-asyncio, plain `def` tests, `CliRunner` + `monkeypatch`).

---

### `tests/parser/examples/coverage/memory_semantic.voss` + `memory_working.voss` (NEW) — D-07

**Analog:** `tests/parser/examples/assistant.voss:1-18`. Self-contained fixtures demonstrating `memory.semantic` and `memory.working` in isolation.

**Reference excerpt** (assistant.voss:3 for semantic; capacity-arg shape from line 2):
```voss
let kb: memory.semantic(source: "./knowledge_base/")
let history: memory.episodic(capacity: 20 turns)
```

**Target shape** (per M3-RESEARCH §"Pattern: parser/analyzer/codegen coverage fixtures"):
```voss
# tests/parser/examples/coverage/memory_semantic.voss
let kb: memory.semantic(source: "./knowledge_base/")
fn lookup(q: string) -> list<string> {
    return kb.retrieve(q, top_k: 3)
}
```
```voss
# tests/parser/examples/coverage/memory_working.voss
let scratchpad: memory.working(capacity: 8)
fn note(content: string) {
    scratchpad.add(content)
}
```

**Adaptation notes:**
- Keep each fixture < 10 LOC and self-contained.
- Parametrize discovery in either (a) extending `tests/parser/test_examples.py:NAMES` tuple with `("coverage/memory_semantic", "coverage/memory_working")`, OR (b) a new `test_examples_coverage.py` that globs `EXAMPLES_DIR/"coverage"/*.voss`. M3-VALIDATION row `coverage-fixtures-parser` uses `-k coverage`, so option (a) keyword-matches naturally — recommend (a).

---

### `tests/analyzer/examples/coverage/` (NEW) — D-07

**Analog:** `tests/analyzer/test_examples.py:1-85` — parametrized `_load(name)` → `analyze(program, emit_indexes=False, index_builder=FakeIndexBuilder())` → assert specific diag codes are absent.

**Reference pattern** (analyzer/test_examples.py:34-41):
```python
def test_classify_example_analyzes_without_probable_warning():
    program = _load("classify.voss")
    result = analyze(
        program,
        emit_indexes=False,
        index_builder=FakeIndexBuilder(),
    )
    assert [d for d in result.diagnostics if d.code == "ANLY001"] == []
```

**Adaptation notes:**
- Either: (a) reuse fixtures at `tests/parser/examples/coverage/` from inside the analyzer test (analyzer/test_examples.py:10 already points at `tests/parser/examples`), and add 2 new test functions covering `memory_semantic`/`memory_working`. (b) Mirror to `tests/analyzer/examples/coverage/` and add a parametrized loop.
- Recommend (a): no new directory, mirrors how the current four examples are loaded from a single parser fixture set. Path: extend `analyzer/test_examples.py` directly with two new `test_memory_semantic_*` / `test_memory_working_*` functions.

---

### `tests/codegen/snapshots/coverage/` (NEW) — D-07

**Analog:** `tests/codegen/test_snapshots.py:14-71` — `_generated_sources(tmp_path)` builds dict of `{name: source}`, asserts `source == snapshot_path.read_text()`, then runs `_assert_readable_snapshot` to enforce no compiler imports / no one-line ifs.

**Reference pattern** (test_snapshots.py:46-65):
```python
def _assert_readable_snapshot(name: str, source: str) -> None:
    ast.parse(source, filename=f"{name}.py")
    _assert_starts_with_imports(source)
    assert ";" not in source
    assert not re.search(r"(?m)^[ \t]*if\b[^\n]*:[ \t]*return\b", source), (
        "snapshot contains one-line if ...: return"
    )
    assert "from voss " not in source
    assert "import voss " not in source
    _assert_no_compiler_imports(source)
    assert source.endswith("\n") and not source.endswith("\n\n")


def test_generated_example_sources_match_snapshots(tmp_path):
    generated = _generated_sources(tmp_path)
    for name, source in generated.items():
        snapshot_path = SNAPSHOTS / f"{name}.py"
        snapshot = snapshot_path.read_text()
        assert source == snapshot
```

**Adaptation notes:**
- Add coverage snapshots under `tests/codegen/snapshots/coverage/memory_semantic.py` and `tests/codegen/snapshots/coverage/memory_working.py`.
- Either extend `test_snapshots.py:_generated_sources` to also include the coverage fixtures, OR add `test_snapshots_coverage.py` that parametrizes over the coverage names. M3-VALIDATION uses `-k coverage` for the test name — keyword match nudges toward a new `test_*coverage*.py` file.
- Reuse `_assert_readable_snapshot` from `test_snapshots.py` (it's module-level; import directly).

---

### `docs/voss-vs-python.md` (NEW) — D-15

**Analog:** None in tree. `docs/` directory does not currently exist.

**Adaptation notes:**
- Top of file: H1 title + one-paragraph framing ("Voss compiles to readable Python. Below: three samples paired with their hand-written equivalents.").
- Per-sample H2 section. For each: brief one-paragraph commentary on what `.voss` makes explicit that raw Python leaves implicit (confidence gates / budgets / lazy semantic match / agent spawn semantics), followed by side-by-side fenced code blocks: `samples/{name}.voss` and `examples/raw_python/{name}.py`.
- Footer: LOC counts table (compute via `wc -l samples/*.voss examples/raw_python/*.py` and embed as a static table; do not script).
- README link target: section header `## Voss vs raw Python` so the README link is `docs/voss-vs-python.md#voss-vs-raw-python` (or top-of-file, simpler).

---

### `README.md` — D-14 + D-15 link

**Analog:** Self. Replace the "Phase 1 status" banner (line 5) with a "What is .voss" section.

**Adaptation notes:**
- Delete or move the "Phase 1 status" blockquote (line 5) — per M3-RESEARCH §"State of the Art" it's outdated.
- New section "## What is .voss" positioned between H1 and "## Install". Frame as: probable values, confidence gates, context budgets, semantic routing, agents/spawn/gather, memory primitives, fallbacks. Explicitly state "not a Python replacement".
- Link to `samples/` (existing) and `docs/voss-vs-python.md` (new, D-15).
- Keep "Project Docs" section (lines 60-65); add `docs/voss-vs-python.md` to that list as a second link to the same doc (per M3-RESEARCH §Open Question Q-5: two links to one doc).
- M3-VALIDATION row `framing-readme` greps for the exact string `"AI workflow control"` and an absence of `"Python replacement"` — use those exact phrasings.

---

## Shared Patterns

### Pattern A: Hermetic stub via PYTHONPATH-prepended sitecustomize
**Source:** `tests/examples/helpers.py:106-118, 201-229` (`_sitecustomize_source` + `deterministic_subprocess_env`).
**Apply to:** Every new or modified test in `tests/examples/` that calls `run_voss` or `run_cmd` against generated code.
**Behavior:** Writes a `sitecustomize.py` under `tmp_path/_voss_stub/`, prepends to `PYTHONPATH`, sets `VOSS_TEST_STUB_RESPONSE`. After M3 D-01 lands, subprocesses inherit `VOSS_HERMETIC=1` from the parent `voss run`. Tests can also set `VOSS_HERMETIC=1` directly in `base_env` (M3-VALIDATION D-11).

**No new code required** — helpers already exist; M3 only consumes.

### Pattern B: Click stderr banner via `err=True`
**Source:** `voss/harness/cli.py:42-50, 55-61` (canonical `click.echo(..., err=True)` for credential diagnostics).
**Apply to:** `voss/cli.py:run` (D-02 banner) and any test asserting on the banner.
**Critical:** `CliRunner` routes stderr to `result.stderr` (NOT `result.output`). Construct runner with `CliRunner(mix_stderr=False)` if separation is needed; subprocess tests via `run_voss` already separate stdout/stderr automatically (helpers.py:50-57).

### Pattern C: Same-PR sample ↔ parity-oracle coupling
**Source:** D-12 + M3-RESEARCH §Pitfall 7.
**Apply to:** Any plan task that edits `samples/support.voss` or `samples/research.voss`.
**Rule:** The matching `examples/raw_python/{support,research}.py` edit MUST land in the same task. Lint check: after task commit, `pytest tests/examples/test_{support,research}_e2e.py -q -k matches_raw` is green.

### Pattern D: Static analyzer call with FakeIndexBuilder
**Source:** `tests/analyzer/test_examples.py:13-24` + `tests/codegen/test_examples.py:26-42`.
**Apply to:** Any new analyzer/codegen test for coverage fixtures, AND the in-process D-03 sentinel in `test_check_speed.py`.
**Behavior:** Pass `index_builder=FakeIndexBuilder()` to `analyze(...)`; with `emit_indexes=False` (post-D-03 fix) the builder is never called, but supplying it documents intent and is the established pattern.

### Pattern E: In-process StubProvider via `register_stub` context manager
**Source:** `tests/examples/helpers.py:94-103` (`register_stub` contextmanager).
**Apply to:** Every test path that runs raw-Python parity oracles in-process (M3-RESEARCH §Pitfall 3).
**Critical:** Wrap BOTH `asyncio.run(module.handleMessage(...))` AND `asyncio.run(raw_handle_message(...))` inside the same `with register_stub(STUB_RESPONSE):` block (see test_research_e2e.py:126-128 for exemplar).

---

## No Analog Found

| File | Role | Data Flow | Notes |
|------|------|-----------|-------|
| `docs/voss-vs-python.md` | docs | static | `docs/` does not exist in tree. No analog. Greenfield prose; structure cribbed from README + paired `examples/raw_python/*.py`. Planner should rely on M3-RESEARCH §"Code Examples" for the per-sample LOC and commentary template. |

---

## Metadata

**Analog search scope:** `voss/`, `voss_runtime/`, `tests/`, `samples/`, `examples/raw_python/`, `docs/`, `README.md`, `.planning/phases/M2-project-cognition/M2-PATTERNS.md` (structural template).

**Files scanned:** 23 (every analog explicitly read or cited from M3-RESEARCH file:line).

**Pattern extraction date:** 2026-05-11.

---

## PATTERN MAPPING COMPLETE

**Phase:** M3 - Language Validation
**Files classified:** 22
**Analogs found:** 22 / 22

### Coverage
- Files with exact analog: 21
- Files with role-match analog: 0
- Files with no analog: 1 (`docs/voss-vs-python.md` — greenfield prose)

### Key Patterns Identified
- **Sibling-in-file extension:** Most M3 changes (analyzer guard, provider hook, sample headers, raw-parity edits) are in-file extensions of code that already follows the target pattern. The `emit_indexes` flag and `register_stub` context manager are the load-bearing reuse points.
- **`auth.resolve(preference="auto")` is the single source of truth for "do we have creds?"** — `voss/harness/cli.py:38-77` is the canonical consumer; `voss/cli.py:run` mirrors it for the auto-stub fallback.
- **Three layers of stub injection already exist** (in-process `register_stub`, in-process encoder patch via `install_support_fake_encoder_in_process`, subprocess sitecustomize via `deterministic_subprocess_env`) — M3 adds zero new injection mechanisms.
- **`tests/parser/examples/assistant.voss` is the canonical reference for `memory.*` + `use`** — both new coverage fixtures and the `samples/support.voss` extension copy patterns from it.
- **Snapshot-and-readability invariants live in `tests/codegen/test_snapshots.py`** — `_assert_readable_snapshot` enforces the LANG-03 readability contract; coverage fixtures should reuse it directly.

### File Created
`/Users/benjaminmarks/Projects/Voss/.planning/phases/M3-language-validation/M3-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference per-file analogs (with file:line citations) when writing each PLAN.md's action sections. Every M3 file has either an exact in-tree analog or an explicit in-file extension target.
