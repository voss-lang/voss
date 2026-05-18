---
phase: M10
plan: 00
type: execute
wave: 0
depends_on: [M9-08]
files_modified: []
autonomous: false
requirements: [CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]
must_haves:
  truths:
    - "M10 execution is blocked until M9-08 has been planned, executed, and summarized."
    - "Wave 0 makes no source changes and no planning doc edits except its own SUMMARY when executed."
    - "The gate validates CodeIntelPanel exists and SubAgentPanel precedence tests pass before any M10 code-intel implementation starts."
    - "The gate validates M10 plans still exclude M11-M15 work, file watch, cross-repo search, completion/hover/diagnostics/rename, new memory classes, and recorder/runtime emit points."
  artifacts:
    - path: ".planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md"
      provides: "Prerequisite CodeIntelPanel amendment plan"
    - path: ".planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md"
      provides: "Evidence that M9-08 executed successfully"
  goal_backward_verification:
    - "Start from the full M10 goal: codebase intelligence requires a TUI landing zone before M10 can wire panel updates."
    - "If M9-08 did not execute, stop here; later M10 plans would otherwise build against a nonexistent UI contract."
    - "If M10 plans contain deferred capability scope, stop here and replan before implementation."
---

<objective>
Block M10 execution until the required M9 CodeIntelPanel prerequisite is actually complete. This plan is a pre-flight gate, not an implementation plan.

Purpose: protect CODE-07 and prevent M10 from writing code against a missing M9 side-region contract. Also re-audit the hard scope fences before source work starts.

Output: a gate SUMMARY that records M9-08 readiness, scope-fence checks, and the exact commands run.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md
@.planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md
@.planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md
@.planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md
</context>

<tasks>

<task type="checkpoint:blocking">
  <name>Task 1: Verify M9-08 exists, executed, and owns CodeIntelPanel</name>
  <requirements>[CODE-07]</requirements>
  <files>none</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-CONTEXT.md (M9 amendment section)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md (Requirement 7)
  </read_first>
  <action>
    Run the prerequisite file and summary checks. Confirm M9-08-SUMMARY.md records a successful self-check and names CodeIntelPanel, SubAgentPanel precedence, and no-new-runtime-hooks verification. If any check fails, stop M10 and write a CHECKPOINT summary explaining that M9-08 must be executed before M10 can continue.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; test -f .planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; test -f .planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "CodeIntelPanel|SubAgentPanel|region-share|runtime" .planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; rg -n "Self-Check: PASSED|Self-check: PASSED|self-check.*PASSED|status: .*complete" .planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md</automated>
  </verify>
  <acceptance_criteria>
    - M9-08-PLAN.md exists and mentions CodeIntelPanel plus SubAgentPanel precedence.
    - M9-08-SUMMARY.md exists and records successful execution.
    - The summary includes no-new-runtime-hooks evidence.
    - If the summary is absent or not passed, this task ends with a blocking checkpoint and no M10 implementation work starts.
  </acceptance_criteria>
</task>

<task type="checkpoint:blocking">
  <name>Task 2: Run prerequisite TUI and scope-fence checks</name>
  <requirements>[CODE-01, CODE-02, CODE-03, CODE-04, CODE-05, CODE-06, CODE-07]</requirements>
  <files>none</files>
  <read_first>
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-SPEC.md (Boundaries, Constraints, Acceptance Criteria)
    - /Users/benjaminmarks/Projects/Voss/.planning/phases/M10-agent-capability-surface-caps-01/M10-VALIDATION.md
    - /Users/benjaminmarks/Projects/Voss/tests/harness/tui/test_code_intel_panel.py
    - /Users/benjaminmarks/Projects/Voss/tests/harness/tui/test_no_new_runtime_hooks.py
  </read_first>
  <action>
    Re-run the M9-08 TUI tests and source-fence greps from the current branch. Then grep M10 plan files for forbidden scope terms and ensure any matches appear only as explicit "deferred", "out of scope", or "forbidden" statements. High-severity scope or runtime-surface drift blocks M10.
  </action>
  <verify>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/tui/test_code_intel_panel.py tests/harness/tui/test_code_intel_region_share.py tests/harness/tui/test_no_new_runtime_hooks.py -q</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -c 'from pathlib import Path; import re, sys; forbidden=re.compile(r"file.?watch|completion|hover|diagnostics|rename|M11|M12|M13|M14|M15|marketplace|MCP bridge|multi-agent in chat|long-running", re.I); allowed=re.compile(r"defer|deferred|out of scope|non-goal|forbidden|scope fence|No completion|No file watch|No file watcher|no file-watch|No new|No backend|not exposed|without file-watch|Security enforcement|Threat ID|long-running LSP server|installed-version diagnostics|test_code_|watchdog|watchfiles|codeAction|code_action", re.I); bad=[]; root=Path(".planning/phases/M10-agent-capability-surface-caps-01"); [bad.append(f"{p}:{i}:{line.strip()}") for p in root.glob("M10-*-PLAN.md") if p.name!="M10-00-PLAN.md" for i,line in enumerate(p.read_text().splitlines(),1) if forbidden.search(line) and not allowed.search(line)]; print("\n".join(bad)); sys.exit(1 if bad else 0)'</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; ! (rg -n "class .*Memory" voss/harness | rg -v "voss/harness/memory_store.py:54:class MemoryStore")</automated>
    <automated>cd /Users/benjaminmarks/Projects/Voss &amp;&amp; python3 -m pytest tests/harness/tui/test_no_new_runtime_hooks.py -q</automated>
  </verify>
  <acceptance_criteria>
    - M9-08 CodeIntelPanel tests pass on the branch M10 will execute from.
    - Runtime-surface baseline still passes.
    - M10 plans contain forbidden follow-on capability names only as deferred or non-goal scope fences.
    - No new memory classes exist in voss/harness before M10 implementation starts.
  </acceptance_criteria>
</task>

</tasks>

<threat_model>
## ASVS L1 Gate

Security enforcement is on. Any high-severity prerequisite failure blocks M10.

| Threat ID | Category | Component | Risk | Mitigation |
|-----------|----------|-----------|------|------------|
| T-M10-00-01 | Integrity | Planning dependency | M10 could execute before its M9 TUI dependency exists. | Hard file, summary, and test gates before Wave 1. |
| T-M10-00-02 | Scope creep | Phase boundary | M10 could absorb M11-M15 capability work. | Scope-fence grep blocks non-deferred follow-on capability references. |
| T-M10-00-03 | Tampering | Runtime baseline | A prerequisite could have changed recorder/runtime emit points. | Existing no-new-runtime-hooks test must pass. |
</threat_model>

<verification>
- `test -f .planning/phases/M9-tui-shell-tui-01/M9-08-PLAN.md`
- `test -f .planning/phases/M9-tui-shell-tui-01/M9-08-SUMMARY.md`
- `python3 -m pytest tests/harness/tui/test_code_intel_panel.py tests/harness/tui/test_code_intel_region_share.py tests/harness/tui/test_no_new_runtime_hooks.py -q`
- `! (rg -n "class .*Memory" voss/harness | rg -v "voss/harness/memory_store.py:54:class MemoryStore")`
- Scope-fence grep over M10 plans for forbidden follow-on capabilities.
</verification>

<success_criteria>
- M9-08 has executed and summarized successfully before any M10 source change begins.
- CodeIntelPanel and region-share tests are green.
- Runtime-surface and memory-class invariants are green.
- The M10 scope fence is clean.
</success_criteria>
