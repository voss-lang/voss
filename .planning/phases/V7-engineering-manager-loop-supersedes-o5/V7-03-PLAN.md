---
phase: V7-engineering-manager-loop-supersedes-o5
plan: 03
type: execute
wave: 3
depends_on: ["V7-02"]
files_modified:
  - .planning/ROADMAP.md
  - .planning/STATE.md
autonomous: true
requirements: [VEM-CLI, VEM-PERSIST, VEM-SIGNOFF]
must_haves:
  truths:
    - "EM cage regress green: dispatch to an undeclared role is denied (EMCageViolation); no set_ceiling/set_p/extend_budget on the handle; kill/rescope lineage + routing_rationale recorded"
    - "Existing O5 em tests pass (79/79); idea→≥1 card→review→terminal→RunFinal proven on stub"
    - "git diff shows zero field changes on RunRecord/SessionRecord/BudgetScope; V7 adds no schema fields and no new deps"
    - "O5 is marked superseded in ROADMAP and STATE; V7 acceptance criteria are all met"
  artifacts:
    - path: ".planning/ROADMAP.md"
      provides: "O5 superseded marker + V7 plan list/goal finalized"
      contains: "superseded"
    - path: ".planning/STATE.md"
      provides: "O5 superseded by V7 + V7 status updated"
      contains: "V7"
  key_links:
    - from: ".planning/phases/V7-.../V7-VALIDATION.md verify rows"
      to: "tests/harness/em/"
      via: "regression run of the shipped cage + lineage suites"
      pattern: "tests/harness/em"
---

<objective>
Close the phase: verify the EM loop + cage invariants regress green after the V7-02 wiring, confirm zero frozen-schema drift and no new dependencies, and do the O5-superseded bookkeeping in ROADMAP/STATE. This proves the composition added in V7-02 did not weaken the cage and did not touch the frozen records.

Purpose: The acceptance criteria #5 (cage regress), #6 (O5 em tests pass), and #7 (zero field changes on RunRecord/SessionRecord/BudgetScope) plus the O5-supersession bookkeeping all land here.

Output: A verification record (em suite + schema-freeze green, git-diff zero-field confirmation) and finalized ROADMAP/STATE entries marking O5 superseded by V7. No production code changes — this plan only runs tests and edits planning docs.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-SPEC.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-VALIDATION.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-RESEARCH.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-02-SUMMARY.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Regress the EM cage + lineage suites and confirm zero frozen-schema drift / no new deps</name>
  <files>(verification only — no source files modified)</files>
  <read_first>
    - tests/harness/em/test_em_handle_cage.py (TestCageInvariant1Introspection: no set_ceiling/set_p/extend_budget; TestCageInvariant2NonRoster: undeclared-role dispatch denied; TestCageInvariant4DoneCardProtection)
    - tests/harness/em/test_em_handle_dispatch.py, tests/harness/em/test_em_lineage.py (kill/rescope lineage + routing_rationale recorded)
    - tests/voss/test_team_backcompat_regression.py (schema-freeze tests, -k schema)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-VALIDATION.md (verify + bookkeeping rows — the exact commands)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-RESEARCH.md (§Security Domain cage trust-boundary table; §Boundaries frozen schemas)
  </read_first>
  <action>
    Run the cage + lineage + full em regression and the schema-freeze test. Confirm acceptance criteria #5/#6/#7 hold AFTER the V7-02 wiring:
    - Cage introspection: no set_ceiling/set_p/extend_budget path on EMBoardHandle.
    - Cage roster check: dispatch to an undeclared role raises EMCageViolation.
    - Lineage: kill/rescope lineage + routing_rationale recorded.
    - Full O5 em suite passes (79/79).
    - Schema-freeze: the backcompat regression `-k schema` is green AND `git diff` shows ZERO field add/remove/rename on RunRecord/SessionRecord/voss_runtime.BudgetScope. Inspect the diff of the session/recorder/voss_runtime budget modules; the only V7 code change should be in voss/harness/cli.py (the run subcommand + 2 helpers) and the new test file — assert no edits to the frozen-record dataclasses.
    - No new deps: confirm pyproject.toml is unchanged (git diff on pyproject.toml is empty for V7).

    Use `.venv/bin/python -m pytest` (bare python3 lacks deps — memory voss-python-interpreter). DO NOT include tests/harness/board/ — 13 pre-existing RED from V6-02..05 (unexecuted) are not V7's concern. If any cage/lineage/em/schema test is RED, STOP and report — it is a V7 regression, not a pre-existing failure.

    No fenced code in this action.
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/em/test_em_handle_cage.py tests/harness/em/test_em_handle_dispatch.py tests/harness/em/test_em_lineage.py -q 2>&1 | tail -4 && .venv/bin/python -m pytest tests/harness/em/ -x -q 2>&1 | tail -3 && .venv/bin/python -m pytest tests/voss/test_team_backcompat_regression.py -k schema -q 2>&1 | tail -4 && git diff --stat -- voss/harness/session.py voss/harness/recorder.py voss_runtime pyproject.toml 2>/dev/null; echo "schema/dep diff stat above MUST show no field changes to RunRecord/SessionRecord/BudgetScope and an unchanged pyproject.toml"</automated>
  </verify>
  <acceptance_criteria>
    - `tests/harness/em/test_em_handle_cage.py`, `test_em_handle_dispatch.py`, `test_em_lineage.py` all green (cage intact: undeclared-role dispatch denied; no set_ceiling/set_p/extend_budget; kill/rescope lineage + routing_rationale recorded).
    - `tests/harness/em/` 79/79 green (idea→≥1 card→review→terminal→RunFinal proven on stub).
    - `tests/voss/test_team_backcompat_regression.py -k schema` green; `git diff` confirms ZERO field changes on RunRecord/SessionRecord/BudgetScope.
    - `pyproject.toml` unchanged by V7 (no new third-party deps).
    - `tests/harness/board/` is NOT referenced in any V7 verification command.
  </acceptance_criteria>
  <done>Cage + lineage + full em suites green; schema-freeze green with zero RunRecord/SessionRecord/BudgetScope field changes; pyproject.toml unchanged; board/ excluded from the gate.</done>
</task>

<task type="auto">
  <name>Task 2: Mark O5 superseded by V7 in ROADMAP and STATE; finalize V7 entry</name>
  <files>.planning/ROADMAP.md, .planning/STATE.md</files>
  <read_first>
    - .planning/ROADMAP.md (Phase V7 block ~line 1924; the existing O→V supersession banner convention from the V0–V12 STATE entry and ORCHESTRATION-PLAN.md)
    - .planning/STATE.md (Phase Status table + Recent Activity format; O6/M13 supersession-marker precedent at lines 62-63)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-SPEC.md (the 7 acceptance criteria + "V7 supersedes O5" statement)
  </read_first>
  <action>
    Bookkeeping only — no code. In ROADMAP.md: the V7 block (~1924) Goal/Scope currently restate the PRD EM-01..10 phase; update the plan list to reference the 3 V7 plans (V7-01 RED scaffold, V7-02 CLI+persist+sign-off, V7-03 verify+bookkeeping) and confirm the "supersedes O5" marker is explicit (the heading already says "supersedes O5"; add a one-line note that O5 artifacts are retained as reference and V7 ships the runnable delta: team run CLI + RunFinal persistence + sign-off). Do NOT rewrite the locked Scope/cage paragraph.

    In STATE.md: update the Phase Status table to mark O5 superseded by V7 (mirror the O6→V9 "⊘ SUPERSEDED by V9" marker style at line 62) and add/refresh a V7 row reflecting completion status after V7-01/02/03. Add a Recent Activity bullet (dated 2026-06-06) summarizing V7: delta on shipped O5 — `voss team run` composing V3–V6 + em_loop, RunFinal sidecar persistence, human approve/reject sign-off (record-only), cage re-verified, zero frozen-schema drift, no new deps; O5 marked superseded. Keep "Current Position" focus unchanged unless the operator has moved it.

    Match the existing doc style (markers, table format, dated bullets — fold, don't sprawl). No fenced code.
  </action>
  <verify>
    <automated>grep -n -i "supersed" .planning/ROADMAP.md | grep -i "O5\|V7" | head; grep -n "V7" .planning/STATE.md | head; echo "ROADMAP V7/O5 supersession marker + STATE V7 entry present above"</automated>
  </verify>
  <acceptance_criteria>
    - ROADMAP.md V7 block lists the 3 V7 plans and states O5 is superseded (artifacts retained as reference); the locked Scope/cage paragraph is unchanged.
    - STATE.md marks O5 superseded by V7 (matching the O6→V9 marker style) and has a dated V7 Recent Activity bullet summarizing the delta + cage re-verify + zero-schema-drift + no-new-deps.
    - No source/code files modified by this task (planning docs only).
  </acceptance_criteria>
  <done>ROADMAP + STATE record O5-superseded-by-V7 and the finalized V7 plan list/summary; doc style matches existing supersession markers.</done>
</task>

</tasks>

<verification>
- Cage + lineage + full em suites green; schema-freeze green; git diff zero-field on frozen records; pyproject.toml unchanged.
- ROADMAP/STATE mark O5 superseded by V7.
- All 7 V7 SPEC acceptance criteria satisfied across V7-01/02/03.
</verification>

<success_criteria>
EM cage regresses green after wiring; no frozen-schema drift; no new deps; O5 marked superseded; phase closeable to `/gsd-verify-work`.
</success_criteria>

<output>
Create `.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-03-SUMMARY.md` when done.
</output>
