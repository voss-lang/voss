---
phase: T3-network-surface
plan: 01
type: execute
wave: 0
depends_on: []
files_modified:
  - tests/harness/test_web_fetch.py
  - tests/harness/test_web_search.py
  - tests/harness/test_allow_net.py
  - tests/harness/test_net_telemetry.py
  - tests/harness/test_rate_limit.py
  - tests/harness/mcp/__init__.py
  - tests/harness/mcp/test_mcp_config.py
  - tests/harness/mcp/test_mcp_client.py
  - tests/harness/mcp/test_mcp_scope.py
  - voss/harness/lifecycle.py
  - tests/harness/test_lifecycle.py
autonomous: true
requirements: [NET-03]
must_haves:
  truths:
    - "All 9 NET-XX test files exist with at least one test stub each, collected by pytest without ImportError"
    - "tests/harness/mcp/ is a Python package (has __init__.py)"
    - "voss/harness/lifecycle.py defines register_subprocess, register_session, reap_all, and an atexit-registered shutdown that walks both registries"
    - "lifecycle.reap_all sends SIGTERM, waits up to 5.0s, then SIGKILL to any subprocess that did not exit"
    - "lifecycle.reap_all calls await session.aclose() on every registered NetSession-shaped object"
    - "pyyaml is present in pyproject.toml main deps (verified by import yaml at test-collection time)"
  artifacts:
    - path: "voss/harness/lifecycle.py"
      provides: "register_subprocess(proc), register_session(session), reap_all() coroutine, atexit hook"
      contains: "def register_subprocess"
    - path: "tests/harness/test_lifecycle.py"
      provides: "Deterministic-mock test that fake-process gets SIGTERM, then SIGKILL after 5s deadline; NetSession-shaped object gets aclose()"
      contains: "def test_sigterm_then_sigkill"
    - path: "tests/harness/mcp/__init__.py"
      provides: "Makes tests/harness/mcp/ a Python package so pytest collects nested files"
      contains: ""
    - path: "tests/harness/test_web_fetch.py"
      provides: "5 NET-01 placeholder tests using pytest.skip(\"pending T3-05\") with named test functions"
      contains: "def test_registration"
    - path: "tests/harness/test_web_search.py"
      provides: "4 NET-02 placeholder tests using pytest.skip(\"pending T3-06\")"
      contains: "def test_no_key"
    - path: "tests/harness/test_allow_net.py"
      provides: "6 NET-05 placeholder tests using pytest.skip(\"pending T3-02\")"
      contains: "def test_default_false"
    - path: "tests/harness/test_net_telemetry.py"
      provides: "5 NET-06 placeholder tests using pytest.skip(\"pending T3-03\")"
      contains: "def test_redact_url_strips"
    - path: "tests/harness/test_rate_limit.py"
      provides: "5 NET-07 placeholder tests using pytest.skip(\"pending T3-04\")"
      contains: "def test_bucket_exhaustion"
    - path: "tests/harness/mcp/test_mcp_config.py"
      provides: "Placeholder NET-03a test stub"
      contains: "def test_loader_parses_fixture"
    - path: "tests/harness/mcp/test_mcp_client.py"
      provides: "Placeholder NET-03b/c test stubs (test_lazy_launch, test_sigterm_reap)"
      contains: "def test_lazy_launch"
    - path: "tests/harness/mcp/test_mcp_scope.py"
      provides: "Placeholder NET-04 test stubs (4 cases)"
      contains: "def test_default_plan_scope"
  key_links:
    - from: "voss/harness/lifecycle.py:reap_all"
      to: "asyncio.subprocess.Process.terminate / .kill"
      via: "loop over _SUBPROCESSES with 5.0s wait_for then kill fallback"
      pattern: "asyncio\\.wait_for\\(proc\\.wait\\(\\), timeout=5\\.0\\)"
    - from: "voss/harness/lifecycle.py:atexit hook"
      to: "asyncio.run(reap_all())"
      via: "atexit.register installs a wrapper that runs reap_all"
      pattern: "atexit\\.register"
---

<objective>
Install Wave 0 test scaffolding so downstream NET-XX feature waves land green-on-first-import: 9 test files with named (but skipped) test functions matching every row in T3-RESEARCH.md's Req→Test map, plus a Python package init for tests/harness/mcp/. Pioneer voss/harness/lifecycle.py — the shared reap hook D-03 locks as the single shutdown point for MCP subprocesses (T3-07) and the NetSession httpx.AsyncClient (T3-05/T3-06). T3-RESEARCH.md confirms NO predecessor exists — this plan is the first author of the lifecycle pattern.

Purpose: NET-03 acceptance (c) "on session exit all spawned MCP subprocesses receive SIGTERM within 5s" depends on this hook existing before MCP code lands. Skipped placeholders give pytest deterministic test ids that later waves un-skip by removing pytest.skip and writing real bodies — every downstream task's `<automated>` command runs without ImportError from day one of execution.

Output: lifecycle.py with register/reap/atexit triad + test asserting SIGTERM-then-SIGKILL deadline; 9 placeholder test files all importable (each contains pytest.skip("pending T3-XX") in the body of every function); tests/harness/mcp/__init__.py.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/T3-network-surface/T3-SPEC.md
@.planning/phases/T3-network-surface/T3-CONTEXT.md
@.planning/phases/T3-network-surface/T3-RESEARCH.md
@.planning/phases/T3-network-surface/T3-PATTERNS.md
@.planning/phases/T3-network-surface/T3-VALIDATION.md
@voss/harness/providers.py
@voss/harness/tools.py
@pyproject.toml
</context>

<interfaces>
From voss/harness/providers.py (aclose pattern to mirror):

```
class AnthropicOAuthProvider:
    def __init__(self, creds, *, client=None, ...):
        self._client = client

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=120.0)
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None
```

T3-RESEARCH.md confirms: NO existing atexit/shutdown hook module is in tree. lifecycle.py is greenfield. T3-PATTERNS.md "No Analog Found" confirms this for lifecycle.py.

The session-shaped object that lifecycle.py will reap is `NetSession` (created by T3-05 in voss/harness/net.py — does not exist yet). lifecycle.py MUST NOT import net.py (circular risk). Instead, the registry stores objects that quack-duck `async def aclose(self) -> None`. T3-test uses a tiny inline duck-typed stub.

Pytest collection invariant: every placeholder test function must have a stable name matching T3-RESEARCH.md Req→Test map (rows NET-01a..NET-07e). This is load-bearing — downstream plans cite these exact test ids in their `<automated>` blocks.
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Create voss/harness/lifecycle.py with SIGTERM+5s+SIGKILL reap + test</name>
  <files>voss/harness/lifecycle.py, tests/harness/test_lifecycle.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-SPEC.md (NET-03 acceptance c — "SIGTERM within 5s and exit code is captured in telemetry")
    - .planning/phases/T3-network-surface/T3-CONTEXT.md (D-03 — "SIGTERM with a 5.0-second deadline before SIGKILL fallback")
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (section "voss/harness/lifecycle.py" — pattern to pioneer)
    - voss/harness/providers.py lines 162-170 (aclose pattern)
    - voss/harness/tools.py lines 210-228 (_shell_capture asyncio.subprocess pattern; note the kill-on-timeout shape)
  </read_first>
  <action>
    Create voss/harness/lifecycle.py. Module-level state: two module-private lists, `_SUBPROCESSES: list[asyncio.subprocess.Process]` and `_SESSIONS: list[object]`. Public API:

    - `register_subprocess(proc: asyncio.subprocess.Process) -> None` — appends proc to _SUBPROCESSES.
    - `register_session(session: object) -> None` — appends any object that has an `async def aclose(self) -> None` method (duck typed; no import of NetSession to avoid circular). Note in module docstring that the contract is "object with awaitable aclose() method".
    - `async def reap_all() -> None` — iterates _SUBPROCESSES: for each proc whose returncode is None, call `proc.terminate()`, then `await asyncio.wait_for(proc.wait(), timeout=5.0)`. On asyncio.TimeoutError, call `proc.kill()` and `await proc.wait()`. Then iterate _SESSIONS: `await session.aclose()` wrapped in try/except (catch BaseException, log via stderr — never raise from reap_all because it's called from atexit). After both passes, clear both module lists.
    - `def reset_for_tests() -> None` — clears both lists; module-private helper exported only for tests.

    Atexit hook: at module import time, register a top-level function `_atexit_hook()` via `atexit.register(_atexit_hook)`. `_atexit_hook` body: if both lists are empty, return. Otherwise call `asyncio.run(reap_all())` inside try/except (catch RuntimeError if a loop is already running; in that case fall back to `asyncio.get_event_loop().run_until_complete(reap_all())` or a fresh `asyncio.new_event_loop()` run). This is the well-known atexit-from-async pain point; document the fallback choice in the docstring.

    Imports: `asyncio`, `atexit`, `sys` (for stderr writes), `from __future__ import annotations`. Stdlib only.

    Create tests/harness/test_lifecycle.py:

    - `test_register_subprocess_terminate_path`: create a real `asyncio.create_subprocess_exec("sleep", "60")` proc, `register_subprocess(proc)`, then `await reap_all()`. Assert `proc.returncode` is not None and the call returned in well under 5 seconds (use time.monotonic delta < 1.0). Use `pytest.mark.skipif` if `sleep` is unavailable (Windows guard — voss is unix-only per ROADMAP T3 constraints, so skip with reason "unix sleep required").
    - `test_register_subprocess_sigkill_fallback`: spawn a subprocess that ignores SIGTERM. Use `python -c "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)"` as the argv. After `register_subprocess(proc)` + `await reap_all()`, assert proc.returncode is not None (process eventually died) and elapsed wall time is between ~4.5 and ~6.5 seconds (5.0s deadline + small kill overhead).
    - `test_register_session_aclose_called`: define an inline class with `async def aclose(self)` that flips a flag; `register_session(stub)`; `await reap_all()`; assert flag is True.
    - `test_aclose_exception_does_not_propagate`: inline class whose `aclose` raises RuntimeError; assert `reap_all()` returns without raising.
    - `test_reset_for_tests_clears_registries`: register stub session + stub fake proc; `reset_for_tests()`; verify both lists empty.

    Use `@pytest.fixture(autouse=True)` calling `reset_for_tests()` before and after each test so module-level state is hermetic.

    Tests are `async def test_*` (pyproject pytest-asyncio mode = auto per T3-PATTERNS metadata).

    Do NOT import voss/harness/net.py or any MCP module. Do NOT register the atexit hook from inside tests.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_lifecycle.py -x -q 2>&amp;1 | tail -20</automated>
  </verify>
  <acceptance_criteria>
    - source assertion: `grep -nE "def register_subprocess|def register_session|async def reap_all|atexit\.register" voss/harness/lifecycle.py | grep -v '^#' | wc -l` returns >= 4
    - source assertion: `grep -nE "wait_for\(.*timeout=5\.0|asyncio\.wait_for" voss/harness/lifecycle.py | grep -v '^#' | wc -l` returns >= 1
    - source assertion: `grep -cE "proc\.kill\(\)" voss/harness/lifecycle.py` returns >= 1 (SIGKILL fallback present)
    - import isolation: `grep -nE "from voss\.harness\.(net|mcp)|import.*voss\.harness\.(net|mcp)" voss/harness/lifecycle.py` returns 0 matches (no downstream imports)
    - behavior: all 5 lifecycle tests pass
    - timing assertion: test_register_subprocess_sigkill_fallback completes within 7 seconds wall time
    - regression: `uv run pytest tests/harness/ -k "lifecycle" -x -q` exit 0
  </acceptance_criteria>
  <done>lifecycle.py exports the four-symbol surface (register_subprocess, register_session, reap_all, reset_for_tests); atexit hook installed at import time; SIGTERM-then-5s-then-SIGKILL behavior proved by deterministic subprocess tests; aclose exceptions are swallowed; module imports nothing from voss/harness/{net,mcp}.</done>
</task>

<task type="auto">
  <name>Task 2: Scaffold 9 NET-XX test files + tests/harness/mcp/__init__.py</name>
  <files>tests/harness/test_web_fetch.py, tests/harness/test_web_search.py, tests/harness/test_allow_net.py, tests/harness/test_net_telemetry.py, tests/harness/test_rate_limit.py, tests/harness/mcp/__init__.py, tests/harness/mcp/test_mcp_config.py, tests/harness/mcp/test_mcp_client.py, tests/harness/mcp/test_mcp_scope.py</files>
  <read_first>
    - .planning/phases/T3-network-surface/T3-RESEARCH.md (section "Validation Architecture" — full 35-row Req→Test map; copy each row's test function name verbatim)
    - .planning/phases/T3-network-surface/T3-VALIDATION.md (Wave 0 Requirements checklist)
    - .planning/phases/T3-network-surface/T3-PATTERNS.md (Shared Patterns "asyncio.run() Wrapper" + "@pytest.fixture + monkeypatch + xdg Pattern")
    - tests/harness/test_agent_config.py (existing analog for xdg+monkeypatch+reset_config pattern from T1-04)
    - tests/harness/test_permissions_modes.py (analog for PermissionGate denial test shape used by test_allow_net.py + mcp/test_mcp_scope.py)
    - pyproject.toml (verify `pyyaml` is in main deps under [project] dependencies; researcher A4 open question)
  </read_first>
  <action>
    Create `tests/harness/mcp/__init__.py` as an empty file (zero bytes) so pytest treats tests/harness/mcp/ as a package and collects nested files.

    For each of the 9 placeholder test files, the file shape is:
    - `from __future__ import annotations` at the top.
    - One-line docstring naming the requirement (e.g., `"""Wave 0 scaffold for NET-01 web_fetch. Bodies land in T3-05."""`).
    - `import pytest`.
    - One `def test_<name>() -> None:` (or `async def` for files where downstream tests will need it) per row in T3-RESEARCH.md's Req→Test map for that file. Body is exactly: `pytest.skip("pending T3-NN — placeholder created by T3-01")` where NN is the downstream plan number (T3-05 for web_fetch, T3-06 for web_search, T3-02 for allow_net, T3-03 for net_telemetry, T3-04 for rate_limit, T3-07 for all mcp/*).

    File-by-file test function name list (copy verbatim from T3-RESEARCH.md rows NET-01a..NET-07e):

    tests/harness/test_web_fetch.py (5 funcs):
    - test_registration  (NET-01a)
    - test_allow_net_gate  (NET-01b)
    - test_truncation  (NET-01c)
    - test_timeout_clamp  (NET-01d)
    - test_http_errors  (NET-01e)

    tests/harness/test_web_search.py (4 funcs):
    - test_no_key  (NET-02a)
    - test_mocked_results  (NET-02b)
    - test_count_clamp  (NET-02c)
    - test_429_handling  (NET-02d)

    tests/harness/test_allow_net.py (6 funcs):
    - test_default_false  (NET-05a)
    - test_toml_true  (NET-05b)
    - test_cli_override  (NET-05c)
    - test_cli_explicit_false  (NET-05d)
    - test_gate_before_prompt  (NET-05e)
    - test_zero_socket_invariant  (NET-05f)

    tests/harness/test_net_telemetry.py (5 funcs):
    - test_redact_url_strips  (NET-06a)
    - test_redact_url_noop  (NET-06b)
    - test_event_emission  (NET-06c)
    - test_mcp_events  (NET-06d)
    - test_run_record_roundtrip  (NET-06e)

    tests/harness/test_rate_limit.py (5 funcs):
    - test_bucket_exhaustion  (NET-07a)
    - test_replenish  (NET-07b)
    - test_toml_override_string  (NET-07c)
    - test_toml_override_table  (NET-07d)
    - test_mcp_bypasses_bucket  (NET-07e)

    tests/harness/mcp/test_mcp_config.py (1 func — NET-03a):
    - test_loader_parses_fixture

    tests/harness/mcp/test_mcp_client.py (2 funcs — NET-03b/c):
    - test_lazy_launch
    - test_sigterm_reap

    tests/harness/mcp/test_mcp_scope.py (4 funcs — NET-04a/b/c/d):
    - test_default_plan_scope
    - test_edit_scope
    - test_scope_denial
    - test_auto_does_not_override_scope

    All function bodies are exactly `pytest.skip("pending T3-NN — placeholder created by T3-01")`. Do NOT write any actual assertions, fixtures, or imports beyond pytest. Downstream plans (T3-02..T3-07) replace these stubs with real test bodies.

    pyyaml verification step (researcher A4 open question): grep pyyaml in pyproject.toml. If absent from `[project]` dependencies, fail the task with a clear error message and instruct executor to add `"pyyaml>=6.0"` to the dependencies list. If present, log to SUMMARY that A4 is resolved.
  </action>
  <verify>
    <automated>uv run pytest tests/harness/test_web_fetch.py tests/harness/test_web_search.py tests/harness/test_allow_net.py tests/harness/test_net_telemetry.py tests/harness/test_rate_limit.py tests/harness/mcp/ --collect-only -q 2>&amp;1 | tail -30</automated>
  </verify>
  <acceptance_criteria>
    - collection assertion: pytest --collect-only reports exactly 32 test ids across the 9 files (5+4+6+5+5+1+2+4 = 32)
    - skip assertion: `uv run pytest tests/harness/test_web_fetch.py tests/harness/test_web_search.py tests/harness/test_allow_net.py tests/harness/test_net_telemetry.py tests/harness/test_rate_limit.py tests/harness/mcp/ -q 2>&amp;1 | tail -3` shows "32 skipped" (or similar; exact count exact)
    - source assertion: `test -f tests/harness/mcp/__init__.py` (file exists, zero or near-zero bytes)
    - source assertion: `grep -l "pytest.skip" tests/harness/test_web_fetch.py tests/harness/test_web_search.py tests/harness/test_allow_net.py tests/harness/test_net_telemetry.py tests/harness/test_rate_limit.py tests/harness/mcp/test_mcp_config.py tests/harness/mcp/test_mcp_client.py tests/harness/mcp/test_mcp_scope.py | wc -l` returns 8 (mcp __init__.py excluded)
    - function name assertion (NET-05f load-bearing): `grep -c "def test_zero_socket_invariant" tests/harness/test_allow_net.py` returns 1
    - pyyaml gate: `grep -c "pyyaml" pyproject.toml` returns >= 1 OR task fails with a clear message
    - regression: `uv run pytest tests/harness/ -x -q --collect-only` exits 0 (no collection errors)
  </acceptance_criteria>
  <done>9 test files created with 32 named-but-skipped test functions matching T3-RESEARCH.md's Req→Test map verbatim; tests/harness/mcp/ is a package; pytest --collect-only reports all 32 ids; pyyaml presence in pyproject.toml verified or task halts.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| Python process exit → spawned subprocesses + open httpx.AsyncClient | At interpreter shutdown, every MCP subprocess and the shared NetSession.AsyncClient must be reaped within a bounded deadline (5.0s SIGTERM + SIGKILL). Failure = orphaned processes consuming user resources or leaked TCP sockets. |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-T3-05 | DoS | lifecycle.reap_all not invoked on crash → MCP subprocess leak | mitigate | atexit registration at module import time; reap_all wrapped in try/except so a single failing aclose never aborts the loop over remaining subprocesses (test_aclose_exception_does_not_propagate proves) |
| T-T3-05b | DoS | misbehaving subprocess ignores SIGTERM | mitigate | wait_for(proc.wait(), timeout=5.0) + proc.kill() fallback path (test_register_subprocess_sigkill_fallback proves wall-time bounded ≤ 6.5s) |
</threat_model>

<verification>
- `uv run pytest tests/harness/test_lifecycle.py -x -q` exits 0 (5 tests pass)
- `uv run pytest tests/harness/test_web_fetch.py tests/harness/test_web_search.py tests/harness/test_allow_net.py tests/harness/test_net_telemetry.py tests/harness/test_rate_limit.py tests/harness/mcp/ -q --collect-only 2>&1 | grep -c "test_"` reports 32
- `uv run pytest tests/harness/ --collect-only -q` exits 0 (no ImportError introduced anywhere)
- `grep -c "pyyaml" pyproject.toml` returns >= 1 (researcher A4 closed)
- `test -f voss/harness/lifecycle.py && test -f tests/harness/mcp/__init__.py` (both exist)
</verification>

<success_criteria>
- voss/harness/lifecycle.py exists with register_subprocess + register_session + reap_all + atexit hook
- 5 lifecycle tests prove SIGTERM-then-5s-then-SIGKILL plus aclose exception safety
- 32 placeholder NET-XX test functions exist with the exact names downstream `<automated>` commands will cite
- pyyaml verified present in pyproject.toml (open question A4 resolved)
- Downstream plans T3-02..T3-09 can cite `pytest tests/harness/test_<file>.py::test_<name>` and pytest will collect the id without ImportError
</success_criteria>

<output>
Create `.planning/phases/T3-network-surface/T3-01-SUMMARY.md` when done: report lifecycle.py public API + SIGKILL fallback wall-time observed; list all 32 placeholder test ids by file; confirm pyyaml is in pyproject.toml (closes researcher open question A4); note that downstream plans will replace `pytest.skip(...)` with real bodies.
</output>
