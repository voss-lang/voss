---
phase: M10
plan: 06
type: execute
wave: 5
depends_on: [M10-04, M10-05]
files_modified:
  - tests/harness/test_code_integration.py
  - tests/harness/test_code_perf.py
  - tests/harness/test_code_invariants.py
  - tests/harness/test_tools.py
  - tests/harness/tui/test_no_new_runtime_hooks.py
  - .planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md
autonomous: false
requirements: [CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]
must_haves:
  truths:
    - "All seven M10 requirements CODE-01..CODE-07 have automated evidence or explicit manual acceptance evidence."
    - "10K-LoC scan target is <= 5s; 100K-LoC target is <= 30s or partial-index warning appears."
    - "No orphan language-server processes remain after normal or interrupted session exit."
    - "Forbidden scope remains absent: no file watch, cross-repo search, completion/hover/diagnostics/rename, new memory classes, or recorder/runtime emit points."
    - "Optional real language-server smoke is recorded when local tools are installed; default suite can skip unavailable servers."
  artifacts:
    - path: "tests/harness/test_code_integration.py"
      provides: "End-to-end fixture coverage for tools, slash, index, LSP fallback, and search fallback"
    - path: "tests/harness/test_code_perf.py"
      provides: "Generated fixture scan latency and partial-index warning checks"
    - path: "tests/harness/test_code_invariants.py"
      provides: "Scope-fence and forbidden-surface regression checks"
  goal_backward_verification:
    - "This final wave starts from the acceptance checklist in M10-SPEC and closes every item with a command or documented manual evidence."
    - "If any requirement lacks evidence, the phase remains incomplete even if focused unit tests pass."
---

<objective>
Close M10 with integrated acceptance, performance sampling, lifecycle/orphan checks, and forbidden-scope invariants.

Purpose: prove the code-intelligence layer works as a coherent feature across index, LSP, ast-grep/regex, tools, slash, context injection, and TUI bridge while preserving hard non-goals.

Output: integration tests, performance tests, invariant tests, optional live-server evidence, and final validation updates.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md
@.planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md
@tests/harness/tui/test_no_new_runtime_hooks.py
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add end-to-end code-intel integration coverage across fixtures</name>
  <requirements>[CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]</requirements>
  <files>tests/harness/test_code_integration.py, tests/harness/test_code_tools.py, tests/harness/test_code_context.py, tests/harness/tui/test_code_intel_integration.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md (all Acceptance Criteria)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md
    - /Users/benjaminmarks/Projects/Voss/tests/fixtures/code
  </read_first>
  <action>
    Add integration tests that run the same fixture set through index build, code_search, find_definition, find_references, code_refresh, `/symbol`, `/refs`, `/refresh`, Project Index context injection, and CodeIntelPanel updates. Tests should use fake LSP server responses by default and real language servers only under optional live markers.

    Ensure each result asserts source-type tags and language fields. Missing servers must prove `lsp_unavailable` with ast-grep or regex fallback, not a crash.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_integration.py tests/harness/test_code_tools.py tests/harness/test_code_context.py tests/harness/tui/test_code_intel_integration.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "CODE-01|CODE-02|CODE-03|CODE-04|CODE-05|CODE-06|CODE-07|lsp_unavailable|regex-fallback|ast-grep" tests/harness/test_code_integration.py</automated>
  </verify>
  <acceptance_criteria>
    - Every CODE-01..CODE-07 requirement is named in integration evidence.
    - Python, JS/TS, Rust, and Go fixtures each participate in definition/reference or graceful-unavailable assertions.
    - `code_refresh` reflects a post-refresh fixture edit.
    - Tool, slash, context, and TUI surfaces share consistent result shapes.
  </acceptance_criteria>
</task>

<task type="checkpoint:human-verify" gate="blocking">
  <name>Task 2: Run performance and orphan-process acceptance checks</name>
  <requirements>[CODE-01, CODE-02, CODE-06]</requirements>
  <files>tests/harness/test_code_perf.py, tests/harness/test_code_lsp.py</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md (latency and orphan-process acceptance)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-RESEARCH.md (Lifecycle/orphan sampling, Performance sampling)
  </read_first>
  <action>
    Add generated-fixture performance tests for 10K-LoC and 100K-LoC synthetic repos. The 10K test should assert scan completes in <= 5 seconds on the local machine or record a clear failure. The 100K test should assert <= 30 seconds or that partial-index warning behavior appears before first turn.

    Add or reuse lifecycle tests that start a fake long-running LSP server, force normal shutdown and interrupt shutdown, then assert no registered child process remains. If optional real servers are installed, run the live smoke and record versions in the SUMMARY. Because timing depends on local hardware, this task is a blocking checkpoint for the executor to record actual results.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_perf.py tests/harness/test_code_lsp.py -q -m "not live"</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_lsp_live.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ps aux | rg "pyright|typescript-language-server|rust-analyzer|gopls" || true</automated>
  </verify>
  <acceptance_criteria>
    - 10K-LoC generated fixture scan is <= 5s or the SUMMARY records a blocking performance failure.
    - 100K-LoC generated fixture is <= 30s or partial-index warning appears before first turn.
    - Fake LSP process cleanup tests prove no orphan remains after normal and interrupted exit.
    - Optional live-server smoke is run when local servers are installed; otherwise skips are recorded with missing command names.
  </acceptance_criteria>
</task>

<task type="auto">
  <name>Task 3: Add final invariant and forbidden-scope gates</name>
  <requirements>[CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]</requirements>
  <files>tests/harness/test_code_invariants.py, tests/harness/tui/test_no_new_runtime_hooks.py, .planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md (Boundaries and Constraints)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md (Deferred Ideas)
    - /Users/benjaminmarks/Projects/Voss/tests/harness/tui/test_no_new_runtime_hooks.py
  </read_first>
  <action>
    Add invariant tests and greps that fail if M10 introduced forbidden scope: file-watch packages or watch loops, cross-repo search, completion/hover/diagnostics/rename APIs, new `class .*Memory` definitions under voss/harness, recorder emit points, or modifications to voss_runtime/{probable,budget,agent}.py baseline.

    Update M10-VALIDATION.md task statuses only after the executor has real green/red evidence. Do not weaken the validation contract.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/test_code_invariants.py tests/harness/tui/test_no_new_runtime_hooks.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n "class .*Memory" voss/harness</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! rg -n "watchdog|watchfiles|file.?watch|completion|hover|diagnostic|rename|formatting|codeAction|code_action" voss/harness/code voss/harness/cli.py voss/harness/tools.py</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; git diff --quiet -- voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py</automated>
  </verify>
  <acceptance_criteria>
    - Invariant tests pass.
    - Greps find no new memory classes and no forbidden LSP/watch features.
    - Git diff is quiet for recorder.py and voss_runtime/{probable,budget,agent}.py.
    - M10-VALIDATION.md reflects actual executed status without removing any required verification row.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## ASVS L1 Gate

Security enforcement is on. Any high-severity unresolved issue blocks phase closeout.

| Threat ID | Category | Component | Risk | Mitigation |
|-----------|----------|-----------|------|------------|
| T-M10-06-01 | DoS | scan/LSP | Performance targets missed or servers orphaned. | Blocking perf/orphan checkpoint with measured evidence. |
| T-M10-06-02 | Scope creep | code package | Deferred M11-M15 features leak into M10. | Forbidden-scope invariant tests. |
| T-M10-06-03 | Information disclosure | context/results | Snippets or raw source leak into Project Index summary. | Context and integration tests assert no snippets and bounded output. |
| T-M10-06-04 | Integrity | runtime baseline | M10 silently changes recorder/runtime emit surfaces. | no-new-runtime-hooks and git diff quiet checks. |
</threat_model>

<verification>
- `python3 -m pytest tests/harness/test_code_index.py tests/harness/test_code_lsp.py tests/harness/test_code_search.py tests/harness/test_code_tools.py tests/harness/test_code_context.py tests/harness/test_code_integration.py tests/harness/test_code_invariants.py -q`
- `python3 -m pytest tests/harness/tui/test_code_intel_panel.py tests/harness/tui/test_code_intel_region_share.py tests/harness/tui/test_code_intel_integration.py tests/harness/tui/test_no_new_runtime_hooks.py -q`
- `python3 -m pytest tests/harness/test_code_perf.py -q -m "not live"`
- `python3 -m pytest tests/harness/test_code_lsp_live.py -q`
- `! rg -n "class .*Memory" voss/harness`
- `! rg -n "watchdog|watchfiles|file.?watch|completion|hover|diagnostic|rename|formatting|codeAction|code_action" voss/harness/code voss/harness/cli.py voss/harness/tools.py`
- `git diff --quiet -- voss/harness/recorder.py voss_runtime/probable.py voss_runtime/budget.py voss_runtime/agent.py`
- `git diff --check -- tests/harness tests/fixtures/code voss/harness .planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md`
</verification>

<success_criteria>
- All 17 M10-SPEC acceptance criteria have automated or recorded manual evidence.
- Focused code-intel and TUI suites are green.
- Performance and orphan-process checks are recorded.
- Hard scope fences remain intact.
- M10 is ready for `/gsd:verify-work`.
</success_criteria>
