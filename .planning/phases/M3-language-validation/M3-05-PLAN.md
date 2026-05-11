---
phase: M3
plan: 05
type: execute
wave: 2
depends_on: [M3-01, M3-02, M3-04]
files_modified:
  - tests/examples/helpers.py
  - tests/examples/test_support_e2e.py
  - tests/examples/test_research_e2e.py
  - tests/examples/test_helpers.py
  - tests/examples/test_live_examples.py
autonomous: true
requirements:
  - LANG-03
  - LANG-04
  - LANG-06
  - LANG-09
  - LANG-10

tags:
  - tests
  - parity
  - hermetic

must_haves:
  truths:
    - "tests/examples/helpers.py:example_source points to REPO_ROOT/'samples' (not tests/parser/examples/) so the e2e suite validates the canonical samples/*.voss extended in M3-04."
    - "tests/examples/test_helpers.py is deleted (D-09: meta-tests on helpers are out of scope)."
    - "tests/examples/test_live_examples.py is deleted (D-09: live verification stays manual; no --live opt-in)."
    - "tests/examples/test_support_e2e.py asserts the memory.episodic extension is exercised by generated Python and matches raw_python parity under same StubProvider seed."
    - "tests/examples/test_research_e2e.py asserts the try/catch + use extensions are present in generated Python AND match raw_python parity."
    - "pytest tests/examples/ -q exits 0 with VOSS_HERMETIC=1 in env (sets the auto-stub path end-to-end per M3-02)."
    - "No test in tests/examples/ requires live provider creds; all subprocess invocations inherit VOSS_HERMETIC=1 via the test environment or the sitecustomize injection."
  artifacts:
    - path: "tests/examples/helpers.py"
      provides: "example_source + copy_example pointing to samples/ instead of tests/parser/examples/"
      contains: "SAMPLES_DIR"
    - path: "tests/examples/test_support_e2e.py"
      provides: "memory.episodic assertion + raw-parity oracle pair under StubProvider"
      contains: "tickets"
    - path: "tests/examples/test_research_e2e.py"
      provides: "try/catch + use assertions on generated Python + raw-parity oracle pair"
      contains: "web search unavailable"
    - path: "tests/examples/test_helpers.py"
      provides: "DELETED per D-09"
      contains: ""
    - path: "tests/examples/test_live_examples.py"
      provides: "DELETED per D-09"
      contains: ""
  key_links:
    - from: "tests/examples/helpers.py::example_source"
      to: "REPO_ROOT/'samples'"
      via: "SAMPLES_DIR constant replacing PARSER_EXAMPLES"
      pattern: "REPO_ROOT.*samples"
    - from: "tests/examples/test_support_e2e.py"
      to: "examples.raw_python.support.handle_message + tickets module attribute"
      via: "register_stub context manager wrapping both in-process calls"
      pattern: "register_stub"
    - from: "tests/examples/test_research_e2e.py"
      to: "examples.raw_python.research.run_research + ContextScope add"
      via: "monkeypatch web_search to raise → both .voss and .py fall back to 'web search unavailable'"
      pattern: "web search unavailable"
---

<objective>
Repoint the e2e suite to consume the canonical samples (per D-09 + D-10 + Pitfall 4), delete the two legacy files per D-09, and extend the support + research e2e tests to validate the M3-04 sample extensions through both the generated-Python and raw-Python parity oracles. After this plan, the entire tests/examples/ suite runs green under VOSS_HERMETIC=1 with no live-provider dependency.

Purpose: Without the helpers.py repoint, the e2e tests silently keep validating the OLD tests/parser/examples/{support,research}.voss (pre-M3 versions) — the M3-04 sample extensions go unvalidated (Pitfall 4). Without the extension assertions in test_support_e2e.py / test_research_e2e.py, the memory.episodic / try-catch / use surfaces never get a green light from CI. This plan closes the validation loop for LANG-03 (raw-parity = readable Python), LANG-09 (samples pass), and LANG-10 (at least one sample runs end-to-end under StubProvider per D-04).

Output:
- `tests/examples/helpers.py` — PARSER_EXAMPLES constant renamed to SAMPLES_DIR and repointed to REPO_ROOT/"samples"; docstrings updated.
- `tests/examples/test_support_e2e.py` — at least one new assertion (or extended existing one) covering the tickets memory.episodic surface end-to-end.
- `tests/examples/test_research_e2e.py` — at least one new assertion covering try/catch (generated Python contains `try:` / `except`) AND one new assertion covering the use lowering (generated Python contains `from voss_runtime.tools import tool`).
- `tests/examples/test_helpers.py` — DELETED.
- `tests/examples/test_live_examples.py` — DELETED.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M3-language-validation/M3-CONTEXT.md
@.planning/phases/M3-language-validation/M3-RESEARCH.md
@.planning/phases/M3-language-validation/M3-PATTERNS.md
@tests/examples/helpers.py
@tests/examples/test_support_e2e.py
@tests/examples/test_research_e2e.py
@tests/examples/test_classify_e2e.py
@tests/examples/test_cli_matrix.py
@samples/support.voss
@samples/research.voss
@examples/raw_python/support.py
@examples/raw_python/research.py

<interfaces>
From tests/examples/helpers.py:22-39 (the repoint target):

```
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

From tests/examples/helpers.py:94-118 (register_stub context manager — used by every in-process raw-parity oracle per RESEARCH §Pitfall 3):

```
@contextlib.contextmanager
def register_stub(default_response: str) -> Iterator[StubProvider]:
    stub = StubProvider(default_response=default_response)
    voss_runtime.providers.register("__stub__", stub)
    configure(default_model="__stub__")
    try:
        yield stub
    finally:
        reset_config()
```

From tests/examples/test_support_e2e.py:30-34 (autouse fixture preserved) + tests/examples/test_support_e2e.py:112-152 (parametrized routing + raw-parity assert):

```
@pytest.fixture(autouse=True)
def _patch_semantic_matcher_in_process(): ...

def test_support_generated_routes_match_raw_python(
    tmp_path: Path,
    user_message: str,
    expected_prefix: str,
):
    ...
    generated_value = asyncio.run(module.handleMessage(user_message))
    raw_value = asyncio.run(raw_handle_message(user_message))
    assert generated_value == expected_prefix + user_message
    assert raw_value == expected_prefix + user_message
    assert generated_value == raw_value
```

From tests/examples/test_research_e2e.py:112-164 — existing raw-parity oracle pattern with register_stub. Confirm exact function signatures by reading the file fully during read_first.

Existing test files NOT modified by this plan:
- tests/examples/__init__.py (keep)
- tests/examples/test_classify_e2e.py (already runs samples/classify.voss correctly after the helpers.py repoint; no extension content from M3-04 affects classify)
- tests/examples/test_cli_matrix.py (already iterates over all three samples via copy_example — automatically picks up extended samples after helpers.py repoint)
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Repoint tests/examples/helpers.py to samples/ and delete the two legacy files (D-09 + Pitfall 4)</name>
  <files>tests/examples/helpers.py, tests/examples/test_helpers.py, tests/examples/test_live_examples.py</files>
  <read_first>
    - tests/examples/helpers.py (lines 1-100 — full top half; verify only PARSER_EXAMPLES and the two functions using it need changes; the register_stub + sitecustomize section below is untouched)
    - tests/examples/test_helpers.py (full file — confirm content; this file is DELETED but we read it to know what to lose)
    - tests/examples/test_live_examples.py (full file — confirm content; this file is DELETED)
    - tests/examples/test_classify_e2e.py (full file — confirm that classify e2e currently calls `copy_example(tmp_path, "classify")`; after repoint it picks up samples/classify.voss automatically — no test code change needed for classify)
    - tests/examples/test_cli_matrix.py (lines 1-50 — confirm the parametrize loop over names; same automatic pickup pattern)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§"Pitfall 4: tests/examples/copy_example copies from tests/parser/examples/ not samples/" — the exact fix; §"State of the Art" §"Tests source .voss from tests/parser/examples/ → samples/")
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/examples/helpers.py (lines 22-39) — D-09 repoint" — adaptation notes)
    - .planning/phases/M3-language-validation/M3-CONTEXT.md (§D-09 + §D-10 — locked decisions)
  </read_first>
  <behavior>
    - tests/examples/helpers.py:22-23 replaces PARSER_EXAMPLES with SAMPLES_DIR pointing to REPO_ROOT/"samples".
    - tests/examples/helpers.py:26-39 example_source and copy_example use SAMPLES_DIR; the FileNotFoundError message says "canonical sample" not "parser example".
    - tests/examples/test_helpers.py does not exist (rm).
    - tests/examples/test_live_examples.py does not exist (rm).
    - All current passing tests in tests/examples/ that call `copy_example(tmp_path, "classify")` / `"support"` / `"research"` automatically resolve to samples/*.voss after the repoint (no test code change in this task).
    - `pytest tests/examples/ -q` exits 0 after the repoint + deletions, with the e2e tests now exercising the M3-04-extended samples (memory.episodic in support, try/catch + use in research).
  </behavior>
  <action>
    1. Open tests/examples/helpers.py. Replace the line `PARSER_EXAMPLES = REPO_ROOT / "tests" / "parser" / "examples"` (line 23) with `SAMPLES_DIR = REPO_ROOT / "samples"`. Use the new constant name throughout the rest of the file.
    2. Update `example_source(name)` body to use SAMPLES_DIR. Update its docstring from "Return path to a canonical parser example .voss source." to "Return path to a canonical sample .voss source (samples/<name>.voss)."
    3. Update `copy_example(tmp_path, name)` docstring from "Copy a parser example into ``tmp_path`` and return the destination." to "Copy a canonical sample into ``tmp_path`` and return the destination."
    4. Update the FileNotFoundError message inside example_source from `f"parser example missing: {path}"` to `f"canonical sample missing: {path}"`.
    5. Update the module docstring at lines 1-6 if it references "Phase 6" or "parser example" specifically — replace with "Shared helpers for tests/examples e2e tests, sourcing samples from samples/." Keep the second sentence about hermetic / no live providers.
    6. Run `git rm tests/examples/test_helpers.py tests/examples/test_live_examples.py` to delete both files. (Or `rm` if git rm fails — the M3 commit at end of plan-phase will pick up the deletion via the git index sweep.)
    7. Run `find tests/examples -name __pycache__ -type d -exec rm -rf {} +` to clear stale bytecode for the deleted test files (per RESEARCH §"Runtime State Inventory" optional clean step).
    8. Do NOT touch any other constant in helpers.py. The PYTHONPATH-prepended sitecustomize logic at lines 106-118 / 201-229 stays intact — those already reference SAMPLES_DIR-independent paths.
    9. Do NOT change `parsers/test_examples.py` constants. The parser-golden tests at tests/parser/test_examples.py keep their own `EXAMPLES_DIR = Path(__file__).parent / "examples"` pointing to tests/parser/examples/ — that's a different test surface (AST goldens, not e2e behavior).
    10. After the edits, run `pytest tests/examples/ -q` with `VOSS_HERMETIC=1` in env. Expected: classify + cli_matrix + check_speed (sentinel only — wave 0 left it as one test) pass; support and research may show new assertion failures because their tests still assume the un-extended .voss bodies — those failures get fixed in Tasks 2 + 3 of this plan.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && test ! -f tests/examples/test_helpers.py && test ! -f tests/examples/test_live_examples.py && grep -c "SAMPLES_DIR" tests/examples/helpers.py && grep -c "PARSER_EXAMPLES" tests/examples/helpers.py | grep -q "^0$" && VOSS_HERMETIC=1 pytest tests/examples/test_classify_e2e.py tests/examples/test_cli_matrix.py tests/examples/test_check_speed.py -v --no-header 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `test -f tests/examples/test_helpers.py` exits 1 (file removed).
    - `test -f tests/examples/test_live_examples.py` exits 1 (file removed).
    - `grep -c "PARSER_EXAMPLES" tests/examples/helpers.py` returns 0.
    - `grep -c "SAMPLES_DIR = REPO_ROOT / \"samples\"" tests/examples/helpers.py` returns 1.
    - `grep -c "canonical sample" tests/examples/helpers.py` returns at least 2 (docstring + error message).
    - `python -c "from tests.examples.helpers import example_source; from pathlib import Path; p = example_source('classify'); assert p == Path('samples/classify.voss').resolve(), p"` exits 0.
    - `python -c "from tests.examples.helpers import example_source; p = example_source('support'); assert p.parts[-2:] == ('samples', 'support.voss'), p.parts"` exits 0.
    - `VOSS_HERMETIC=1 pytest tests/examples/test_classify_e2e.py tests/examples/test_cli_matrix.py tests/examples/test_check_speed.py -q` exits 0 (classify + matrix + sentinel still green after repoint).
  </acceptance_criteria>
  <done>Helpers repoint complete; legacy files deleted; non-touched e2e tests pass against the extended samples; remaining support/research test extensions land in Tasks 2 + 3.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Extend tests/examples/test_support_e2e.py to validate memory.episodic surface end-to-end (D-05 + D-12)</name>
  <files>tests/examples/test_support_e2e.py</files>
  <read_first>
    - tests/examples/test_support_e2e.py (full file 1-224 lines — confirm the existing structure: autouse semantic-matcher patch fixture, _import_generated_module helper, parametrized routing test, _patch_research_in_process-style helpers, the raw-parity assertion at line 144-151, the voss-run-matches-compile test at 194-225)
    - samples/support.voss (post-M3-04 — confirm tickets declaration line + .add + .last lines exist)
    - examples/raw_python/support.py (post-M3-04 — confirm tickets module-scope EpisodicMemory + tickets.add inside handle_message)
    - tests/examples/helpers.py post-Task-1 (confirm SAMPLES_DIR repoint took effect; example_source('support') returns samples/support.voss path)
    - voss_runtime/memory/episodic.py (lines 33-67 — confirm `.add(content, *, role=...)` mutates self.turns and `.last(n)` reads self.turns[-n:])
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/examples/test_support_e2e.py — D-05 + D-12" — adaptation notes; recommendation: extend the existing test_support_generic_falls_through_to_stub at line 154 OR add a new test that calls handleMessage twice and asserts tickets.last(2) contains both messages via the module's tickets attribute)
  </read_first>
  <behavior>
    - One new assertion (or extended existing test) verifies that `tickets` attribute is exposed on the imported generated module (e.g., `module.tickets`) and is an EpisodicMemory instance with `capacity == 50` after import.
    - One new test or extended test calls `module.handleMessage(...)` twice (within `register_stub(...)`) and asserts `len(module.tickets.turns) >= 2` (two user messages were recorded) AND `module.tickets.last(2)` contains both messages with role "user".
    - The same shape is asserted for the raw_python parity oracle: import examples.raw_python.support, call `raw_handle_message(...)` twice, assert `raw_python.support.tickets.last(2)` mirrors.
    - Both in-process calls are inside the same `with register_stub(...)` block per RESEARCH §Pitfall 3 / Pattern E.
    - Existing tests in the file (4-5 functions) continue to pass after these edits — no regression.
    - `VOSS_HERMETIC=1 pytest tests/examples/test_support_e2e.py -q` exits 0.
  </behavior>
  <action>
    1. Open tests/examples/test_support_e2e.py. Read the file fully — identify:
       a. The autouse fixture for semantic-matcher patching (lines 30-34).
       b. The `_import_generated_module(path, name="voss_generated_support")` helper around line 37.
       c. The existing parametrized routing test at line 112-152.
       d. The fall-through test at line 154-191.
       e. The voss-run-matches-compile test at line 194-224.
    2. Add a new test function `test_support_tickets_memory_records_user_messages` BELOW the existing `test_support_generic_falls_through_to_stub` (so file ordering remains logical). Function signature: `def test_support_tickets_memory_records_user_messages(tmp_path: Path):`.
    3. Body:
       a. Use the existing `copy_example(tmp_path, "support")` + the existing in-process compile machinery (mirroring how test_support_generic_falls_through_to_stub at line 154 sets up — same .voss source resolution, same compile, same module import).
       b. Wrap the test body in `with register_stub("stubbed-response") as stub:` per Pattern E. ALL `asyncio.run(module.handleMessage(...))` calls and `asyncio.run(raw_handle_message(...))` calls live inside this block.
       c. `assert isinstance(module.tickets, type(module.EpisodicMemory(capacity=1)))` (or simpler: `from voss_runtime import EpisodicMemory; assert isinstance(module.tickets, EpisodicMemory) and module.tickets.capacity == 50`).
       d. Call `asyncio.run(module.handleMessage("First user message — please help."))`.
       e. Call `asyncio.run(module.handleMessage("Second user message — still stuck."))`.
       f. Assert `len(module.tickets.turns) >= 2`.
       g. Assert at least 2 of the turns have `role == "user"` and `content` containing "user message".
       h. Mirror with the raw oracle: `from examples.raw_python.support import handle_message as raw_handle_message, tickets as raw_tickets`; reset `raw_tickets.turns.clear()` before the two raw calls (because module-scope state persists between imports). Call `raw_handle_message` twice with the same two messages. Assert `len(raw_tickets.turns) >= 2`.
    4. Do NOT modify the existing `test_support_generated_routes_match_raw_python` parametrized test — the M3-04 sample extension adds new behavior (tickets.add at function entry) which may shift stdout. If the existing test fails after Task 1 because the generated and raw stdouts diverge (e.g., one includes the rendered tickets, the other doesn't), inspect: in test_support_e2e.py the expected_prefix is `[escalated]` / `[refund flow]` / `[auth support]` — those routes don't go through the ctx block and so are unaffected by `include tickets.last(6)`. The fall-through case is the one that consumes tickets.last. If a regression appears, debug by running raw and generated separately; the most likely cause is the raw_python file failing to mirror the codegen `include` shape — re-read M3-04 Task 2 output for the rendering pattern.
    5. Do NOT change the autouse fixture. Do NOT change `_inject_support_helpers`. Do NOT touch the voss-run-matches-compile test at line 194 (that's for LANG-10).
    6. Run `VOSS_HERMETIC=1 pytest tests/examples/test_support_e2e.py -v` after the edit. Expected: all existing tests pass + the new tickets test passes.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && VOSS_HERMETIC=1 pytest tests/examples/test_support_e2e.py -v --no-header 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_support_tickets_memory_records_user_messages" tests/examples/test_support_e2e.py` returns 1.
    - `grep -c "module.tickets" tests/examples/test_support_e2e.py` returns at least 2 (instance check + length check).
    - `grep -c "raw_tickets" tests/examples/test_support_e2e.py` returns at least 2.
    - `grep -c "EpisodicMemory" tests/examples/test_support_e2e.py` returns at least 1.
    - `grep -c "register_stub" tests/examples/test_support_e2e.py` returns at least 1 (the new test uses Pattern E).
    - `VOSS_HERMETIC=1 pytest tests/examples/test_support_e2e.py -v` reports all tests passing (existing + new).
    - `VOSS_HERMETIC=1 pytest tests/examples/test_support_e2e.py::test_support_tickets_memory_records_user_messages -v` exits 0.
  </acceptance_criteria>
  <done>memory.episodic surface validated end-to-end through both generated Python and raw_python; parity invariant holds.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: Extend tests/examples/test_research_e2e.py to validate try/catch + use surfaces end-to-end (D-06 + D-12)</name>
  <files>tests/examples/test_research_e2e.py</files>
  <read_first>
    - tests/examples/test_research_e2e.py (full file 1-201 lines — confirm test_research_compile_python_happy_path_matches_raw at the parity-pattern reference around line 112-134, the timeout/fallback test, and the budget-exceeded path that mirrors the existing raw try/except BudgetExceededError block)
    - samples/research.voss (post-M3-04 — confirm `use voss_runtime::tools::tool` is line 4 and the try { ... } catch e { ... } block wraps webSearch)
    - examples/raw_python/research.py (post-M3-04 — confirm the new try/except Exception block around web_search inside Researcher.run)
    - voss/codegen.py (lines 126-148 — `use` lowering: `use voss_runtime::tools::tool` → `from voss_runtime.tools import tool`; verify the exact emitted line so the grep test is correct)
    - voss/codegen.py (lines 1107-1126 — `try/catch e` lowering to `try: ... except Exception as e: ...` or similar — verify exact emitted shape)
    - .planning/phases/M3-language-validation/M3-PATTERNS.md (§"tests/examples/test_research_e2e.py — D-06 + D-12" — adaptation notes; recommendation: extend test_research_compile_python_happy_path_matches_raw OR add a new sibling test)
    - .planning/phases/M3-language-validation/M3-RESEARCH.md (§Code Examples for research.voss — confirms target shape)
  </read_first>
  <behavior>
    - A new test (or extended existing one) asserts that the generated Python from samples/research.voss contains:
      (a) the substring `from voss_runtime.tools import tool` (proves the `use` lowering),
      (b) the substring `try:` AND `except` AND `"web search unavailable"` (proves the try/catch lowering).
    - A new test (or extended existing one) monkeypatches webSearch / web_search to RAISE a synthetic exception (`raise RuntimeError("forced failure")`) and asserts both generated and raw oracles complete the run successfully AND produce stdout containing the fallback text "web search unavailable" (or whatever the StubProvider response becomes — at minimum, neither raises uncaught and both produce non-empty stdout).
    - Both in-process calls (generated + raw) are inside the same `register_stub(...)` block.
    - Existing tests in the file continue to pass.
    - `VOSS_HERMETIC=1 pytest tests/examples/test_research_e2e.py -q` exits 0.
  </behavior>
  <action>
    1. Read tests/examples/test_research_e2e.py fully. Identify:
       a. Whether it has an `_import_generated_module` helper analogous to test_support_e2e.py.
       b. The raw-parity assertion shape (around line 112-134 per PATTERNS).
       c. The timeout-fallback test that already exercises the BudgetExceededError path.
       d. How copy_example + compile are invoked for research.voss.
    2. Add a new test function `test_research_generated_contains_use_and_try_catch_lowerings`. Body:
       a. `src = copy_example(tmp_path, "research")`.
       b. Compile in-process: same shape as the existing happy-path test compiles. After compile, read the generated .py file as text.
       c. `generated_source = (tmp_path / ".voss-cache" / ...).read_text()` — find the exact path by reading how the existing test resolves it.
       d. `assert "from voss_runtime.tools import tool" in generated_source, generated_source[:500]` (the use lowering).
       e. `assert "try:" in generated_source` (the try/catch lowering — Python try keyword).
       f. `assert "except" in generated_source` (the except keyword).
       g. `assert "web search unavailable" in generated_source` (the fallback string literal preserved through codegen).
    3. Add a new test function `test_research_forced_web_search_failure_matches_raw_fallback`. Body:
       a. Wrap in `with register_stub("stub-summary"):`.
       b. monkeypatch the generated module's web_search (or the runtime tool that backs it) to raise: `monkeypatch.setattr(module, "webSearch", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("forced")))` — or whatever shape works given how codegen names the symbol; if uncertain, inspect the generated source from Task 3's step 2c and pick the actual identifier name.
       c. Run `asyncio.run(module.runResearch("AcmeCo"))` — must not raise. Capture return.
       d. monkeypatch examples.raw_python.research.web_search to raise the same.
       e. Run `asyncio.run(raw_run_research("AcmeCo"))` — must not raise. Capture return.
       f. Assert both returns are non-empty strings.
       g. Optional: assert the strings are equal (full parity) — feasible because both fall back to the same Synthesizer path under StubProvider.
    4. Do NOT modify the existing happy-path or BudgetExceededError tests.
    5. If the monkeypatch path is brittle (because `webSearch` is captured as a closure inside the generated agent class), simplify the second test to just assert that under normal (no-monkeypatch) StubProvider conditions, `runResearch` exits non-empty for both .voss-generated and .py-raw paths — that asserts the try/catch lowering is at least syntactically wired (Python parses the generated source as confirmed by the first test). The hard fallback test can be deferred to manual verification if monkeypatching is impractical.
    6. Run `VOSS_HERMETIC=1 pytest tests/examples/test_research_e2e.py -v` after edits — all tests must pass.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss && VOSS_HERMETIC=1 pytest tests/examples/test_research_e2e.py -v --no-header 2>&1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - `grep -c "def test_research_generated_contains_use_and_try_catch_lowerings" tests/examples/test_research_e2e.py` returns 1.
    - `grep -c "from voss_runtime.tools import tool" tests/examples/test_research_e2e.py` returns at least 1 (the assertion).
    - `grep -c "web search unavailable" tests/examples/test_research_e2e.py` returns at least 1.
    - `grep -c "try:" tests/examples/test_research_e2e.py` returns at least 1 (the assertion target; the colon distinguishes it from any narrative `try`).
    - `VOSS_HERMETIC=1 pytest tests/examples/test_research_e2e.py -v` reports all tests passing.
    - `VOSS_HERMETIC=1 pytest tests/examples/test_research_e2e.py::test_research_generated_contains_use_and_try_catch_lowerings -v` exits 0.
  </acceptance_criteria>
  <done>try/catch + use surfaces validated through generated Python source inspection AND through the runtime forced-failure path; parity holds.</done>
</task>

</tasks>

<verification>
- `VOSS_HERMETIC=1 pytest tests/examples/ -q --no-header 2>&1 | tail -15` exits 0 (full e2e suite green hermetically).
- `pytest tests/examples/ -q --no-header 2>&1 | tail -15` exits 0 (suite green even without env-var — auto-stub kicks in via M3-02's auth.resolve path when developer has no creds).
- `test ! -f tests/examples/test_helpers.py` exits 0.
- `test ! -f tests/examples/test_live_examples.py` exits 0.
- `python -c "from tests.examples.helpers import example_source; p = example_source('classify'); assert 'samples' in str(p) and 'parser/examples' not in str(p)"` exits 0.
- `find tests/examples -name __pycache__ -type d` returns nothing (cleanup confirmed; or harmlessly returns one fresh __pycache__ from this run — both acceptable).
</verification>

<success_criteria>
- D-09 + D-10: tests/examples/ is the test directory; helpers point at samples/; two legacy files removed; no --live opt-in.
- D-11: every test in tests/examples/ runs hermetically — no live-cred dependency in the suite.
- D-12: raw-python parity oracles validated end-to-end for both memory.episodic (support) and try/catch+use (research) surfaces.
- Pitfall 4 mitigated: e2e tests now exercise the M3-04 sample extensions, not pre-M3 fixtures.
- LANG-03 readability backed by raw-parity stdout assertions (existing tests + new ones).
- LANG-09 + LANG-10 unblocked for M3-06's speed gate to land cleanly.
</success_criteria>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| test-time .voss source resolution | A wrong helpers.py constant silently routes the e2e suite to the wrong canonical source; pitfall already documented (Pitfall 4). |
| in-process raw oracle | examples.raw_python.* modules are imported into the test process; mutable module-scope state (e.g., the new `tickets` object) leaks between tests if not cleared. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-M3-18 | Tampering | helpers.py:example_source silently returns the wrong fixture (the legacy tests/parser/examples/ version) → M3-04 extensions go unvalidated | mitigate | Task 1 replaces PARSER_EXAMPLES with SAMPLES_DIR and updates FileNotFoundError + docstrings; acceptance criteria greps for the new constant and asserts the old name is absent. |
| T-M3-19 | Information Disclosure | The raw `tickets` (EpisodicMemory) module-scope object accumulates turns across tests, leaking state between test functions and producing flaky pass/fail patterns | mitigate | Task 2 explicitly resets `raw_tickets.turns.clear()` at the start of the new test; the existing parametrized test does not touch tickets (its routes bypass the ctx block), so no leak. |
| T-M3-20 | Repudiation | The forced-failure web_search test in Task 3 silently no-ops because the monkeypatch targets the wrong symbol (closure-captured webSearch vs. module-scope) | mitigate | Task 3 step 5 allows simplification to a "just assert non-empty under StubProvider" form if monkeypatching is brittle — the syntactic try/catch presence is already proven by Task 3 step 2 (text-grep on generated source). |
| T-M3-21 | Spoofing | Developer's local ANTHROPIC_API_KEY makes the suite pass via live providers, hiding a hermetic-mode regression | mitigate | All tests use `register_stub` context manager (in-process) OR run subprocesses via run_voss with `VOSS_HERMETIC=1` in env (per helpers.py:201-229 + this plan's verification commands). |
| T-M3-22 | Tampering | Stale __pycache__ from test_helpers.py / test_live_examples.py causes pytest to attempt to collect deleted files | mitigate | Task 1 step 7 explicitly clears tests/examples/__pycache__. |
</threat_model>

<output>
After completion, create `.planning/phases/M3-language-validation/M3-05-SUMMARY.md` documenting: (1) the helpers.py diff showing SAMPLES_DIR replacement, (2) the two new test function names in test_support_e2e.py + test_research_e2e.py with one-sentence purpose each, (3) the confirmed deletion of test_helpers.py + test_live_examples.py, (4) the green test counts (pre + post) for tests/examples/, (5) the hand-off to M3-06: the per-sample wall-clock gate can now land into the existing tests/examples/test_check_speed.py file (sentinel already present from M3-01), and the framing docs are independent.
</output>
