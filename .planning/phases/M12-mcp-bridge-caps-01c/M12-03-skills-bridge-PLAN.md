---
phase: M12-mcp-bridge-caps-01c
plan: 03
type: execute
wave: 2
depends_on: [M12-01]
files_modified:
  - voss/harness/mcp/server_skills.py
  - tests/harness/mcp/test_mcp_server_skills.py
autonomous: true
requirements: [MCP-03]

must_haves:
  truths:
    - "`voss/harness/mcp/server_skills.py` exposes `make_skill_dispatch(cwd, provider, history, record, tools, gate, skill_registry) -> Callable[[str, list[str]], Awaitable[str]]`"
    - "The returned async callable looks up the skill id in `skill_registry`, builds a minimal `ctx` SimpleNamespace, calls `entry.handler(ctx, args)` inside a stdout-capture (`contextlib.redirect_stdout`), and returns the captured stdout text"
    - "An unknown skill id raises `KeyError` from the bridge (the dispatcher in M12-02 catches it and converts to `isError=True` envelope per its own contract)"
    - "Skill handlers are invoked synchronously inside `asyncio.to_thread` so that any blocking work (e.g. `asyncio.run(run_turn(...))` inside an agentic skill) does not deadlock the server's event loop"
    - "The bridge's stdout capture is per-invocation (uses a fresh `io.StringIO` each call) — no cross-call contamination"
    - "The bridge does NOT import any specific skill module (`voss.harness.skills.*`); it only consumes the `SkillEntry.handler` callable from the passed registry, so adding/removing skills in T7-style requires no edits here"
  artifacts:
    - path: "voss/harness/mcp/server_skills.py"
      provides: "skill-execution bridge: SkillEntry.handler -> async (name, args) -> stdout-text adapter"
      contains: "def make_skill_dispatch"
      min_lines: 50
    - path: "tests/harness/mcp/test_mcp_server_skills.py"
      provides: "tests that one read-only skill (voss-lint-as-skill) actually runs through the bridge and returns its stdout; unknown skill raises; mutating skill returns its (mode-permitted) output"
      contains: "async def test_voss_lint_as_skill_runs_through_bridge"
      min_lines: 60
  key_links:
    - from: "voss/harness/mcp/server_skills.py"
      to: "voss/harness/skill_registry.py:7"
      via: "SkillHandler = Callable[[Any, list[str]], None]; the bridge satisfies the Any-ctx contract"
      pattern: "entry\\.handler\\("
    - from: "voss/harness/mcp/server_skills.py"
      to: "voss/harness/skills/analyze.py:25"
      via: "ctx shape mirrors what every skill handler unpacks: ctx.cwd, ctx.provider, ctx.history, ctx.record, ctx.renderer, ctx.tools, ctx.gate"
      pattern: "SimpleNamespace\\("
---

<objective>
Build the skill-execution bridge that M12-02's dispatcher will inject as
`skill_dispatch`. Implements D-05 (server-side `run_turn` charges the
server's provider config) and the skill half of MCP-03 (advertisement +
dispatch of the 7 T7 skills).

The bridge is a thin adapter: given a skill id + `args: list[str]`, build a
`SimpleNamespace` ctx that satisfies every existing `SkillEntry.handler`
caller's expectations (`ctx.cwd`/`provider`/`history`/`record`/`renderer`/
`tools`/`gate`), capture stdout, return the captured text. The actual skill
handlers (T7 deliverables) are unchanged.

Parallel-safe with M12-02 (Wave 2): file-disjoint, both depend only on
M12-01.
</objective>

<context>
@.planning/phases/M12-mcp-bridge-caps-01c/M12-CONTEXT.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-PLAN-OUTLINE.md
@.planning/phases/M12-mcp-bridge-caps-01c/M12-01-server-scaffold-PLAN.md

Read first:
- `voss/harness/skill_registry.py` (full file — `SkillEntry`, `SkillHandler =
  Callable[[Any, list[str]], None]`, every inner handler unpacks `ctx.cwd`,
  `ctx.provider`, `ctx.history`, `ctx.record`, `ctx.renderer`, `ctx.tools`,
  `ctx.gate` — that's the SimpleNamespace shape).
- `voss/harness/skills/analyze.py` (full file — confirms `run()` kwargs
  consumed by `_handle_analyze`).
- `voss/harness/skills/voss_lint_as_skill.py` (full file — read-only path,
  deterministic; the easiest end-to-end skill to exercise in tests).
- `voss/harness/skills/summarize_diff.py` (full file — agentic path; confirms
  the bridge can also drive `run_turn`-based skills).
- `voss/harness/render.py` (`PlainRenderer` / `make_renderer` — pick a
  non-TTY renderer for the bridge so skill output goes to stdout, not the
  TUI Console).

D-05 implication: the bridge passes the server's `provider` reference; if the
calling MCP host invokes a skill that runs `run_turn`, the LLM cost lands on
the server's configured provider keys, not the host's. M12-04 surfaces this in
`voss mcp serve --help` text.
</context>

<threat_model>
| ID | Threat | Mitigation |
|---|---|---|
| T-M12-03-01 | Skill stdout writes during one MCP call leak into the next | Each call constructs a fresh `io.StringIO()` and uses `contextlib.redirect_stdout(buf)`. The buffer is local to the call. No module-level state. |
| T-M12-03-02 | Blocking skill (agentic, runs `asyncio.run(run_turn)`) deadlocks the server's event loop | Skill handlers are sync per the `SkillHandler` contract. The bridge wraps the synchronous handler call in `asyncio.to_thread(...)` so a blocking `asyncio.run` inside the skill runs in a worker thread (separate event loop), not the server's loop. |
| T-M12-03-03 | Bridge couples to a specific skill module → breaks when T7's set changes | Bridge takes `skill_registry` as input and looks up by id; imports NO concrete skill module. Adding/removing entries in `default_skill_registry()` requires zero edits in this file. |
| T-M12-03-04 | Long-running skill blocks indefinitely (no host timeout) | OUT OF SCOPE for v0.1: MCP spec leaves cancellation/timeout to the host. The bridge does NOT add a server-side timeout because the server is foreground (host owns timeout via its subprocess kill). M12-05's acceptance test does not exercise multi-minute skills. |

Out-of-scope: skill execution permission policy (M12-02's gate does that
first). Skill cost attribution back to host (unsolved upstream, deferred in
CONTEXT). `CallToolResult` envelope shape (M12-02 owns; this bridge only
returns text).
</threat_model>

<tasks>

<task type="auto">
  <name>Task 1: Create `voss/harness/mcp/server_skills.py` with `make_skill_dispatch` factory</name>
  <read_first>
    voss/harness/skill_registry.py (handler-contract types, ctx field usage)
    voss/harness/skills/analyze.py (definitive ctx-field surface)
    voss/harness/mcp/server_skills.py (file being created — confirm it does not exist)
  </read_first>
  <action>
    Create `voss/harness/mcp/server_skills.py`.

    Imports:
    - `from __future__ import annotations`
    - `import asyncio`, `import contextlib`, `import io`
    - `from pathlib import Path`
    - `from types import SimpleNamespace`
    - `from typing import Any, Awaitable, Callable`

    Public factory:

    ```
    def make_skill_dispatch(
        *,
        cwd: Path,
        provider,
        history,
        record,
        renderer,
        tools,
        gate,
        skill_registry,
    ) -> Callable[[str, list[str]], Awaitable[str]]:
        async def dispatch(name: str, args: list[str]) -> str:
            entry = skill_registry.get(name)
            if entry is None:
                raise KeyError(f"unknown skill: {name}")
            ctx = SimpleNamespace(
                cwd=cwd,
                provider=provider,
                history=history,
                record=record,
                renderer=renderer,
                tools=tools,
                gate=gate,
                skill_registry=skill_registry,
            )
            buf = io.StringIO()

            def _run() -> None:
                with contextlib.redirect_stdout(buf):
                    entry.handler(ctx, list(args))

            await asyncio.to_thread(_run)
            return buf.getvalue()

        return dispatch
    ```

    Notes:
    - `skill_registry=skill_registry` is also placed on the ctx because some
      analyzer/cli skills inspect `ctx.skill_registry` (verified at
      `voss/harness/cli.py:457`). Setting it costs nothing.
    - `asyncio.to_thread` is the deadlock mitigation per T-M12-03-02.
    - `list(args)` defensively-copies the input; the handler must not mutate
      the caller's list.
    - No `try/except` here — exceptions propagate to the M12-02 dispatcher,
      which converts them to `isError=True` envelopes.

    Do NOT import any concrete skill module (`from voss.harness.skills.*`).
    Do NOT import `make_toolset` or `default_skill_registry` — callers
    provide them.
  </action>
  <verify>
    <automated>python3 -c "import ast; ast.parse(open('voss/harness/mcp/server_skills.py').read()); print('ast ok')"</automated>
    <automated>python3 -c "import inspect; from voss.harness.mcp.server_skills import make_skill_dispatch; sig=inspect.signature(make_skill_dispatch); params=list(sig.parameters); assert params==['cwd','provider','history','record','renderer','tools','gate','skill_registry'], params; print('sig ok')"</automated>
    <automated>python3 -c "import re; s=open('voss/harness/mcp/server_skills.py').read(); assert 'asyncio.to_thread' in s, 'must run skill in thread to avoid event-loop deadlock'; assert 'redirect_stdout' in s, 'must capture stdout'; assert 'from voss.harness.skills' not in s, 'must not import specific skill modules'; print('decoupled ok')"</automated>
  </verify>
  <acceptance_criteria>
    - `voss/harness/mcp/server_skills.py` parses and exposes `make_skill_dispatch(*, cwd, provider, history, record, renderer, tools, gate, skill_registry)`
    - Returned async dispatcher uses `asyncio.to_thread` AND `contextlib.redirect_stdout(io.StringIO())`
    - Unknown skill id raises `KeyError("unknown skill: <id>")`
    - Module contains no `from voss.harness.skills.` import (decoupled from T7's concrete set)
  </acceptance_criteria>
  <done>Bridge module ready; per-call stdout capture; thread-isolated skill execution.</done>
</task>

<task type="auto">
  <name>Task 2: Add `tests/harness/mcp/test_mcp_server_skills.py` covering one real skill end-to-end</name>
  <read_first>
    voss/harness/mcp/server_skills.py (Task 1 output)
    voss/harness/skill_registry.py (default_skill_registry — the registry to feed)
    voss/harness/skills/voss_lint_as_skill.py (deterministic, no provider — easiest end-to-end smoke through the bridge)
    tests/skills/fixtures/voss-lint/bad.voss (the seeded ANLY001 fixture from T7)
  </read_first>
  <action>
    Create `tests/harness/mcp/test_mcp_server_skills.py`.

    Tests:

    1. `async def test_voss_lint_as_skill_runs_through_bridge(tmp_path)`:
       - Copy `tests/skills/fixtures/voss-lint/bad.voss` into `tmp_path`.
       - Build: `from voss.harness.tools import make_toolset; tools =
         make_toolset(tmp_path)`. `from voss.harness.skill_registry import
         default_skill_registry; reg = default_skill_registry()`.
       - `from voss.harness.render import PlainRenderer`; `from
         voss.harness.permissions import PermissionGate`; `import types`.
       - `disp = make_skill_dispatch(cwd=tmp_path, provider=None, history=None,
         record=types.SimpleNamespace(model="fake", id="t"),
         renderer=PlainRenderer(), tools=tools, gate=PermissionGate(auto_yes=True),
         skill_registry=reg)`
       - `text = await disp("voss-lint-as-skill", [str(tmp_path)])`
       - `import json; schema = json.loads(text)`; assert
         `schema["version"] == 1`, `schema["findings"]` non-empty, and at
         least one finding has `rule == "ANLY001"`.

    2. `async def test_unknown_skill_raises_key_error(tmp_path)`:
       - Build dispatch as above.
       - `with pytest.raises(KeyError, match="unknown skill: nope"):
         await disp("nope", [])`.

    3. `async def test_dispatch_runs_in_thread_not_blocking_loop(tmp_path)`:
       - Stub a fake skill registry whose handler does
         `time.sleep(0.05)` + `print("done")`. Wrap it as a SimpleNamespace
         with `.get(name)` returning a SimpleNamespace with `.handler` and
         `.id`/`.mutating` fields (mimicking `SkillEntry`).
       - In the asyncio loop, schedule `disp(...)` AND
         `asyncio.sleep(0.001)` concurrently with `asyncio.gather`. Assert
         both completed and the dispatch returned `"done\n"`. (The
         `to_thread` path means the loop wasn't blocked.)

    4. `async def test_per_call_stdout_isolation(tmp_path)`:
       - Stub a fake registry whose handler prints its second arg item.
       - `r1 = await disp("x", ["alpha"])`; `r2 = await disp("x", ["beta"])`.
       - Assert `r1 == "alpha\n"` and `r2 == "beta\n"` (no cross-call leak).
  </action>
  <verify>
    <automated>python3 -m pytest -q tests/harness/mcp/test_mcp_server_skills.py</automated>
    <automated>python3 -m pytest -q tests/harness/mcp/  # full mcp suite</automated>
  </verify>
  <acceptance_criteria>
    - 4 named async tests in `tests/harness/mcp/test_mcp_server_skills.py`, all green
    - The real `voss-lint-as-skill` test asserts schema v1 + ANLY001 finding through the bridge end-to-end
    - The thread-isolation test passes (proves `asyncio.to_thread` wiring)
    - The per-call isolation test passes (proves fresh `StringIO` per call)
    - Full mcp suite still green
  </acceptance_criteria>
  <done>Bridge proven end-to-end on one deterministic skill; thread + stdout isolation verified.</done>
</task>

</tasks>

<verification>
```bash
cd /Users/benjaminmarks/Projects/Voss

# 1. Module decoupled from concrete skill modules
! grep -E "^from voss\\.harness\\.skills\\." voss/harness/mcp/server_skills.py

# 2. Thread + stdout-capture invariants present
grep -q "asyncio.to_thread" voss/harness/mcp/server_skills.py
grep -q "redirect_stdout" voss/harness/mcp/server_skills.py

# 3. Tests green
python3 -m pytest -q tests/harness/mcp/test_mcp_server_skills.py
python3 -m pytest -q tests/harness/mcp/

# 4. Wave-2 file-disjointness: M12-02 file unmodified
test -e voss/harness/mcp/server_tools.py && (git diff --stat voss/harness/mcp/server_tools.py | grep -qE '\S' && echo "FAIL: M12-02 file edited" || echo "OK: M12-02 file untouched") || echo "OK: M12-02 file does not exist yet (Wave 2 sibling)"

# 5. Whitespace
git diff --check
```
</verification>

<success_criteria>
- `voss/harness/mcp/server_skills.py` exists; `make_skill_dispatch` factory takes 8 kw-only args and returns an async `(name, args) -> str` callable.
- Bridge runs skill handlers via `asyncio.to_thread` with per-call `io.StringIO()` stdout capture.
- Bridge imports no concrete skill module; reads only from the passed `skill_registry`.
- Unknown skill id raises `KeyError`.
- 4 tests in `tests/harness/mcp/test_mcp_server_skills.py` green incl. real `voss-lint-as-skill` end-to-end roundtrip; full mcp suite green.
- File-disjoint from M12-02 (`server_tools.py`) and M12-01 surfaces.
- `git diff --check` clean.
</success_criteria>

<output>
Create `.planning/phases/M12-mcp-bridge-caps-01c/M12-03-SUMMARY.md` when done.
</output>
