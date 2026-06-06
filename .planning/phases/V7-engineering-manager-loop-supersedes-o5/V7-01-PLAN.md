---
phase: V7-engineering-manager-loop-supersedes-o5
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - tests/harness/test_team_run_cli.py
autonomous: true
requirements: [VEM-CLI, VEM-PERSIST, VEM-SIGNOFF]
must_haves:
  truths:
    - "A failing test suite encodes the full V7 acceptance surface BEFORE implementation (RED)"
    - "Every VEM-* acceptance criterion maps to a named test in test_team_run_cli.py"
    - "Test bodies drive the REAL planned surface (voss team run CLI, run-final.json shape, click.prompt sign-off) — not an ad-libbed fake API"
  artifacts:
    - path: "tests/harness/test_team_run_cli.py"
      provides: "RED scaffold: TestTeamRunCLI, TestRunFinalPersist, TestSignOff"
      contains: "class TestTeamRunCLI"
      min_lines: 80
  key_links:
    - from: "tests/harness/test_team_run_cli.py"
      to: "voss.harness.cli (team run subcommand, not yet implemented)"
      via: "CliRunner().invoke(root, ['team', 'run', ...])"
      pattern: "team.*run"
---

<objective>
Create the RED scaffold test file `tests/harness/test_team_run_cli.py` that encodes the V7 acceptance criteria as failing tests, BEFORE any implementation in cli.py. This is Wave 0 per V7-VALIDATION.md — the Nyquist contract requires the acceptance surface to exist as runnable tests first.

Purpose: Lock the contract. The tests describe exactly what `voss team run` must do (compose stack, pre-spawn ≥1 card, persist RunFinal, prompt sign-off, record decision) so the implementation in V7-02 has an unambiguous target. RED now → GREEN after V7-02.

Output: `tests/harness/test_team_run_cli.py` with three classes (`TestTeamRunCLI`, `TestRunFinalPersist`, `TestSignOff`) covering all 10 Wave-0 rows in V7-VALIDATION.md. All tests fail (command does not exist yet) — this is correct and expected.
</objective>

<execution_context>
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/workflows/execute-plan.md
@/Users/benjaminmarks/Projects/Voss/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/ROADMAP.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-SPEC.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-CONTEXT.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-RESEARCH.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-VALIDATION.md
@.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-PATTERNS.md

<interfaces>
<!-- The REAL planned surface these tests must drive. Extracted from V7-RESEARCH.md (all VERIFIED via direct execution). -->

CLI surface (V7-02 will create):
  voss team run "<goal>" [--cwd .] [--max-iterations 50]
  - @team_group.command("run") on the existing team group (cli.py:3777)
  - composes _default_team_config() OR compile_team(.voss/team.voss) → SessionTreeManager → Board.from_team_config(..., reviewer=<single slot>) → pre-spawn board.spawn_card(risk_tier="med") → asyncio.run(em_loop(idea=goal, em_handle=..., em_agent=DeterministicEMStub, ...)) → _persist_run_final → print summary → click.prompt(approve/reject) → record decision
  - exits 0 on stub provider

RunFinal (voss/harness/em/tickets.py:112) — EXACTLY 10 fields, frozen+slots:
  root_id, idea, total_cards, done_count, blocked_count, killed_count, rescope_count, em_iterations, ts, kind
  (NO evidence_refs / diff_summary / residual — do NOT assert on those)

run-final.json sidecar shape (V7-02 will write):
  path: <cwd>/.voss/sessions/<root_id>/run-final.json
  body: dataclasses.asdict(rf) (the 10 fields) PLUS a superset "sign_off" key {"decision": "approve"|"reject", "ts": ...}

Test infra (from V7-PATTERNS.md, analog tests/harness/test_team_check_cli.py:36-48):
  root fixture: click.Group("voss"); cli.register(g)
  CliRunner().invoke(root, ["team", "run", "build API", "--cwd", str(tmp_path)], input="approve\n")
  _write(tmp_path, src) helper writes tmp_path/.voss/team.voss
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Write RED scaffold test_team_run_cli.py (TestTeamRunCLI, TestRunFinalPersist, TestSignOff)</name>
  <files>tests/harness/test_team_run_cli.py</files>
  <read_first>
    - tests/harness/test_team_check_cli.py (root fixture lines 36-40, _write helper 43-48, CliRunner invoke 53)
    - tests/harness/em/conftest.py (stub_recorder fixture 79-82: SessionTreeNode.create_root + SessionTreeManager; base_gate 103-104)
    - voss/harness/em/tickets.py:112 (RunFinal — the 10 real fields; do NOT invent evidence_refs/diff_summary/residual)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-VALIDATION.md (Per-Task Verification Map — the 10 W0 rows define the exact test names)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-RESEARCH.md (§Code Examples, §Common Pitfalls — pre-spawn card, async-in-CliRunner, model-tier monkeypatch)
    - .planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-PATTERNS.md (test file analogs + CliRunner input= pattern)
  </read_first>
  <action>
    Create class-based pytest file. Copy the `root` fixture verbatim from test_team_check_cli.py (click.Group("voss"); cli.register(g)) and the `_write(tmp_path, src)` helper. These tests are RED — the `team run` command does not exist yet, so CliRunner invocations will exit non-zero / raise; assertions encode the TARGET behavior so they go GREEN after V7-02.

    Heed memory `gsd-scaffold-fictional-api`: test bodies MUST drive the real planned surface named in `<interfaces>` — `["team", "run", goal, "--cwd", str(tmp_path)]`, reading `<cwd>/.voss/sessions/<root_id>/run-final.json`, asserting the 10 RunFinal fields + `sign_off`. Do NOT stub out a fake `team_run` function, do NOT use `pytest.mark.xfail(strict=False)` (that masks scaffold drift as false-green). If a test cannot find root_id without running, glob `tmp_path/.voss/sessions/*/run-final.json` (single dir expected) rather than hardcoding.

    Per V7-RESEARCH Pitfall 7: default-roster construction calls `get_model_tiers()`; add a fixture or module-level `monkeypatch`/autouse fixture that configures model tiers so `_default_team_config()` resolves (patch `voss.harness.config.get_model_tiers` to return a mapping covering the DEFAULT_ROSTER tiers, or set the env the harness reads). Document the monkeypatch target in a comment so V7-02 stays consistent.

    CliRunner tests are SYNC (no `@pytest.mark.asyncio`) — the command body runs `asyncio.run(...)` internally and CliRunner has no running loop (Pitfall 4).

    TestTeamRunCLI (integration, drive via CliRunner with input="approve\n"):
      - test_stub_run_exits_zero — VEM-CLI: invoke team run with no team file → exit_code == 0 (assert with res.output on failure).
      - test_produces_card_and_run_final — VEM-CLI: after run, glob the sidecar; assert it exists and total_cards >= 1 (pre-spawned med card). Stub path lands the card Blocked → blocked_count >= 1, all-cards-terminal.
      - test_default_roster_fallback — VEM-CLI fallback: no .voss/team.voss → run completes (exit 0) using DEFAULT_ROSTER (7 roles).
      - test_team_file_override — VEM-CLI fallback: write a minimal valid .voss/team.voss via _write → run uses that roster/ceiling, exit 0. (Use a team source that compile_team accepts; mirror test_team_check_cli.py's valid fixture.)
    TestRunFinalPersist (unit, may call _persist_run_final directly once V7-02 exports it; until then assert via the sidecar produced by a CliRunner run):
      - test_fields_serialized — VEM-PERSIST: sidecar JSON contains exactly the 10 RunFinal field keys (root_id, idea, total_cards, done_count, blocked_count, killed_count, rescope_count, em_iterations, ts, kind).
      - test_rereadable — VEM-PERSIST: json.loads(sidecar.read_text()) succeeds without re-running; idea round-trips the goal string.
    TestSignOff (integration, CliRunner with input=):
      - test_prompt_appears — VEM-SIGNOFF: res.output contains the RunFinal summary and the approve/reject prompt text.
      - test_approve_recorded — VEM-SIGNOFF: input="approve\n" → sidecar["sign_off"]["decision"] == "approve".
      - test_reject_recorded_no_revert — VEM-SIGNOFF: input="reject\n" → sidecar["sign_off"]["decision"] == "reject" AND the session node files under .voss/sessions/<root_id>/ that existed are unchanged (record-only; capture file set/mtimes before reading sidecar, assert no node JSON deleted/added by the reject path).

    No fenced code in this action; identifiers and signatures are in <interfaces>. Use `.venv/bin/python` semantics (the file is plain pytest; runner choice is in <verify>).
  </action>
  <verify>
    <automated>.venv/bin/python -m pytest tests/harness/test_team_run_cli.py --co -q 2>&1 | grep -c "::" ; echo "collected (expect 10 test ids)"; .venv/bin/python -m pytest tests/harness/test_team_run_cli.py -q 2>&1 | tail -5</automated>
  </verify>
  <acceptance_criteria>
    - File `tests/harness/test_team_run_cli.py` exists and collects without ImportError (collection-time imports resolve; the COMMAND not existing must cause assertion/exit-code FAILURES at run time, not collection errors).
    - Exactly the 10 named tests collect across classes TestTeamRunCLI (4), TestRunFinalPersist (2), TestSignOff (3) — count is 9 named here; the 10th VEM-PERSIST "run_final_persisted" existence check lives in TestTeamRunCLI as test_run_final_persisted (add it → 10 total, matching V7-VALIDATION rows).
    - All tests are RED (fail) — `voss team run` is not implemented yet. A green result here is a DEFECT (means the surface was faked).
    - No `xfail(strict=False)`, no fake `team_run` stub function; every test drives the real `["team","run",...]` CLI path and reads `.voss/sessions/<root_id>/run-final.json`.
    - A model-tier monkeypatch/autouse fixture is present (named target documented in a comment) so default-roster construction won't raise VossTeamConfigError in V7-02.
  </acceptance_criteria>
  <done>10 tests collect (TestTeamRunCLI: test_stub_run_exits_zero, test_produces_card_and_run_final, test_default_roster_fallback, test_team_file_override, test_run_final_persisted; TestRunFinalPersist: test_fields_serialized, test_rereadable; TestSignOff: test_prompt_appears, test_approve_recorded, test_reject_recorded_no_revert), all RED, driving the real planned CLI surface.</done>
</task>

</tasks>

<verification>
- `tests/harness/test_team_run_cli.py` collects 10 tests, all RED.
- No fake API stand-ins; every test exercises `["team", "run", ...]` via CliRunner.
- Existing `tests/harness/em/` remains 79/79 green (this plan adds no production code): `.venv/bin/python -m pytest tests/harness/em/ -x -q`.
</verification>

<success_criteria>
RED scaffold exists encoding all VEM-CLI/PERSIST/SIGNOFF acceptance criteria; tests fail because the command is absent; the scaffold drives the real planned surface (no fictional API).
</success_criteria>

<output>
Create `.planning/phases/V7-engineering-manager-loop-supersedes-o5/V7-01-SUMMARY.md` when done.
</output>
