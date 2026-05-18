---
phase: M10
plan: 05
type: execute
wave: 4
depends_on: [M10-04]
files_modified:
  - voss/harness/agent.py
  - voss/harness/cli.py
  - voss/harness/code/context.py
  - voss/harness/code/service.py
  - voss/harness/tui/renderer.py
  - voss/harness/tui/app.py
  - tests/harness/test_code_context.py
  - tests/harness/test_happy_path_integration.py
  - tests/harness/tui/test_code_intel_integration.py
autonomous: true
requirements: [CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]
must_haves:
  truths:
    - "Session-start scan runs before the first user turn for chat/do/resume when enabled."
    - "`## Project Index` is a separate bounded system-context section with no raw snippets."
    - "Default Project Index budget is 1500 tokens with explicit truncation marker on overflow."
    - "Scan disabled or failed means no Project Index section and no user-visible traceback."
    - "M10 consumes M9-08 CodeIntelPanel APIs; it does not reimplement the panel widget."
    - "No new recorder emit points or runtime hook changes are introduced."
  artifacts:
    - path: "voss/harness/code/context.py"
      provides: "Bounded `## Project Index` renderer"
    - path: "voss/harness/agent.py"
      provides: "System block injection point for project_index_text"
    - path: "voss/harness/cli.py"
      provides: "Session-start code-index scan and TUI panel update bridge"
  goal_backward_verification:
    - "CODE-06 is only useful if the agent sees the index before planning the first turn."
    - "CODE-07 is only complete if slash/tool results reach the M9 CodeIntelPanel without violating SubAgentPanel precedence."
---

<objective>
Wire project-index context injection and the M9 CodeIntelPanel bridge into the harness session path.

Purpose: expose codebase intelligence automatically to the model and visually to the TUI while keeping scan failures silent, prompt size bounded, and runtime emit surfaces unchanged.

Output: `## Project Index` renderer, session-start scan wiring, run_turn system-block integration, and TUI panel update bridge for `/symbol`, `/refs`, and refresh/index state.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md
@.planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md
@voss/harness/agent.py
@voss/harness/cli.py
@voss/harness/tui/renderer.py
@voss/harness/tui/app.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Render bounded Project Index context and inject it into system blocks</name>
  <requirements>[CODE-01, CODE-06]</requirements>
  <files>voss/harness/code/context.py, voss/harness/code/service.py, voss/harness/agent.py, tests/harness/test_code_context.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/agent.py (_compose_cognition_prompt and _compose_system_blocks)
    - /Users/benjaminmarks/Projects/Voss/tests/harness/test_voss_md_injection.py (provider system block capture pattern)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md (Redaction integration and Auto-injection)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-PATTERNS.md (System prompt injection)
  </read_first>
  <action>
    Add `voss/harness/code/context.py` with `render_project_index_section(summary, token_count=None, max_tokens=1500)`. The section must start with `## Project Index`, include file counts by language, top modules by symbol count, and entry points, and include no raw snippets.

    Extend agent.py's system block composition with an optional `project_index_text` argument. Insert it as its own block after durable project cognition/VOSS context and before prior-turn or loop-specific instructions. Preserve the existing cache_control behavior on the final block.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_context.py -q -k "render or system_blocks"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m py_compile voss/harness/code/context.py voss/harness/agent.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "Project Index|project_index_text|max_tokens=1500|truncated" voss/harness/code/context.py voss/harness/agent.py tests/harness/test_code_context.py</automated>
  </verify>
  <acceptance_criteria>
    - Fresh session system blocks include `## Project Index` with non-zero fixture counts.
    - Section stays at or below 1500 tokens by the repo's token-count approximation.
    - Overflow adds an explicit `(truncated)` marker.
    - Section contains no raw code snippets from fixture files.
    - With scan disabled or summary absent, no Project Index section is emitted and no traceback occurs.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 2: Run session-start scan for chat, do, and resume</name>
  <requirements>[CODE-01, CODE-06]</requirements>
  <files>voss/harness/cli.py, voss/harness/code/service.py, tests/harness/test_happy_path_integration.py, tests/harness/test_code_context.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (_run_repl, do_cmd, resume flow)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cognition.py (existing load flow)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md (M10-06 injection row)
  </read_first>
  <action>
    Build or refresh the code index at session start for `voss chat`, `voss do`, and `voss resume` when code-intel scan is enabled. Use the service's scan budget settings from `.voss/lsp.yml` or defaults. If scan exceeds the quick budget, surface a partial-index warning in the service result and continue without blocking the first turn beyond the locked budget.

    Thread the rendered project_index_text into run_turn. Keep scan failures silent from the model except for omitted Project Index; log/fallback events through existing telemetry style only if a telemetry path already exists. Do not add recorder emit points.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_context.py tests/harness/test_happy_path_integration.py -q -k "project_index or code_index or resume"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "project_index_text|CodeIntelService|partial" voss/harness/cli.py voss/harness/code/service.py</automated>
  </verify>
  <acceptance_criteria>
    - `voss do` fixture path builds `.voss-cache/code/index.db` before provider call.
    - `voss chat` and `voss resume` share the same session-start scan path or a documented helper.
    - Disabled scan omits Project Index cleanly.
    - Scan failure does not crash the session.
    - No file watcher or background watch task is introduced.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Bridge slash/query results to M9 CodeIntelPanel</name>
  <requirements>[CODE-05, CODE-07]</requirements>
  <files>voss/harness/cli.py, voss/harness/tui/renderer.py, voss/harness/tui/app.py, tests/harness/tui/test_code_intel_integration.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/renderer.py (M9-08 private CodeIntelPanel methods)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/tui/app.py (M9-08 side-region owner state)
    - /Users/benjaminmarks/Projects/Voss/voss/harness/cli.py (slash handlers)
  </read_first>
  <action>
    When TextualRenderer is active, update CodeIntelPanel on initial index summary, `/symbol` results, `/refs` results, and `/refresh`. Use only M9-08 private renderer/app methods. Do not import CodeIntelPanel inside service code and do not make code-intel backend depend on Textual.

    Add integration tests that dispatch `/symbol` and `/refs` through the registry with a TextualRenderer/App test double and assert panel state updates. Also test that active SubAgentPanel precedence still wins and CodeIntelPanel state restores after gather.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/tui/test_code_intel_integration.py tests/harness/tui/test_code_intel_region_share.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n "from voss\\.harness\\.tui|TextualRenderer|CodeIntelPanel" voss/harness/code</automated>
  </verify>
  <acceptance_criteria>
    - `/symbol` updates CodeIntelPanel results when TextualRenderer is active.
    - `/refs` updates CodeIntelPanel results when TextualRenderer is active.
    - `/refresh` updates the idle tree/summary.
    - Backend code under `voss/harness/code/` has no import dependency on TUI modules.
    - SubAgentPanel precedence and restore behavior remains green.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## ASVS L1 Gate

Security enforcement is on. High-severity prompt leakage, TUI/backend coupling, or runtime hook drift blocks completion.

| Threat ID | Category | Component | Risk | Mitigation |
|-----------|----------|-----------|------|------------|
| T-M10-05-01 | Information disclosure | Project Index prompt | Context could inject raw source snippets or secrets. | Render counts/modules only; no snippets; bounded to 1500 tokens. |
| T-M10-05-02 | DoS | Session start scan | Large repo could delay first turn indefinitely. | Scan budgets and partial-index warning; no watch mode. |
| T-M10-05-03 | Integrity | TUI bridge | Backend could depend on Textual and break plain mode. | Enforce no TUI imports under voss/harness/code. |
| T-M10-05-04 | Tampering | Runtime hooks | Context bridge could add recorder emit points. | no-new-runtime-hooks test remains part of final closeout. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_code_context.py tests/harness/test_happy_path_integration.py -q -k "project_index or code_index or resume"`
- `python3 -m pytest tests/harness/tui/test_code_intel_integration.py tests/harness/tui/test_code_intel_region_share.py -q`
- `python3 -m py_compile voss/harness/code/context.py voss/harness/agent.py voss/harness/cli.py`
- `! rg -n "from voss\\.harness\\.tui|TextualRenderer|CodeIntelPanel" voss/harness/code`
- `! rg -n "watchdog|watchfiles|file.?watch" voss/harness/code voss/harness/cli.py`
- `git diff --check -- voss/harness/agent.py voss/harness/cli.py voss/harness/code voss/harness/tui tests/harness/test_code_context.py tests/harness/tui/test_code_intel_integration.py`
</verification>

<success_criteria>
- `## Project Index` appears in system context when scan succeeds and is absent when disabled/failing.
- Session-start scan covers chat, do, and resume without file-watch infrastructure.
- CodeIntelPanel receives initial and query results in Textual mode.
- Plain/headless backend paths remain decoupled from TUI imports.
</success_criteria>
